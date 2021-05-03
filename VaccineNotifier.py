import sys
from datetime import datetime, timedelta
import os
import time
import json
import requests
import time
import csv
import boto3
import configparser
import ast
import logging


class VaccineEntry:
    """
     class for vaccine entry
     """
    def __init__(self, hospital_name, age_limit, available_capacity, slots, location):
        self.hospital_name = hospital_name
        self.age_limit = age_limit
        self.slots = slots
        self.location = location
        self.available_capacity = available_capacity


def get_covid_centers(district_num, date_id):
    """
         Function to call API to get list of centers
         @param district_num: District id
         @param date_id:Date
    """
    try:
        url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={district_id}" \
              "&date={date}".format(district_id=district_num, date=date_id)
        response = requests.get(url)
        return json.loads(response.text)
    except Exception as exp:
        logging.error('Obtained Exception while getting data from Cowin api: %s', str(exp))


def parse_data(response, date_id):
    """
     Function to parse API Response
     @param response: API Response
     @param date_id:Date
    """
    api_response_dict = eval(response)
    total_number_centers = len(api_response_dict["centers"])
    try:
        if total_number_centers > 0:
            day = []
            for d in range(1, 7):
                day.append((datetime.strptime(date_id, '%d-%m-%Y') + timedelta(days=d)).strftime('%d-%m-%Y'))
            api_parse_entry = [[]] * len(day)
            district_name = api_response_dict["centers"][0]["district_name"]
            for entry in api_response_dict["centers"]:
                for session in entry["sessions"]:
                    if session["available_capacity"] > 0:
                        if day.count(session["date"]) > 0:
                            index = day.index(session["date"])
                            hospital_name = entry["block_name"]
                            age_limit = session["min_age_limit"]
                            slots = session["slots"]
                            available_capacity = session["available_capacity"]
                            location = "https://www.google.com/maps/search/?api=1&query={block_name}&{district_name}".format(
                                block_name=hospital_name, district_name=entry["district_name"])
                            obj = VaccineEntry(hospital_name, age_limit, available_capacity, slots, location)
                            api_parse_entry[index].append(obj)
                        else:
                            continue
            create_table(api_parse_entry, day, district_name)
        else:
            raise ValueError("No centers available")
    except Exception as exp:
        logging.warning('Exception obtained while processing centers data %s', str(exp))


def create_table(api_parse_entry, day, district_name):
    """
      Function to process the  input and apply custom logic to create CSV file for consumption
      @param api_parse_entry: API Response
      @param district_name:name of the district
    """
    try:
        filename = district_name + ".csv"
        setpath = os.getcwd() + "/output/" + filename
        file = open(setpath, 'w', newline='')
        writer = csv.writer(file)
        for i in range(0, len(day)):
            date_entry = "Date: " + day[i]
            writer.writerow([date_entry])
            writer.writerow(["Hospital Name", "Age Limit", "No of Slots Available", "Slot Timings", "Map Location"])
            for value in api_parse_entry[i]:
                writer.writerow(
                    [value.hospital_name, value.age_limit, value.available_capacity, value.slots, value.location])
            writer.writerow("\n")
            writer.writerow("\n")
        file.close()
        upload(filename)
        message = "https://test-bucket-sathyaam.s3.ap-south-1.amazonaws.com/" + filename
        check = 0
        for i in api_parse_entry:
            check = check + len(i)
        if check > 0:
            sns_notification(message, district_name)
        else:
            sns_notification("No Open slots found ", district_name)
    except Exception as ep:
        logging.error('Exception obtained while creating consolidated table data %s', str(ep))


def upload(filename):
    """
        Function to upload the processed file to S3
        @params filename: lname of the file to be used as S3 key.
    """
    try:
        s3_client = boto3.client('s3')
        s3_client.upload_file(filename, "test-bucket-sathyaam", filename, ExtraArgs={
            'GrantRead': 'uri="http://acs.amazonaws.com/groups/global/AllUsers"',
        })
    except Exception as e:
        logging.error('Obtained Exception while uploading the file: %s', str(e))


def sns_notification(file_location, district_name):
    """
    Function to Send SMS Notification to Subscribers
    @params file_location: location of the result file.
    @param district_name: District name
    """
    try:
        body = 'This weeks Covid vaccine availability/slots for the district ' + district_name + ': ' + file_location
        topic = "arn:aws:sns:ap-south-1:638182133372:covidebuzzer-sns-notificatio" + "-" + district_name
        sns = boto3.client('sns')
        sns.publish(TopicArn=topic,
                    Message=body)
    except Exception as e:
        logging.error('Obtained Exception while sending notification: %s', str(e))


if __name__ == '__main__':
    """
    Main Controller Function    
    """
    logging.basicConfig(filename='/tmp/vaccine-notifier.log', level=logging.DEBUG)
    os.environ['TZ'] = 'Asia/Kolkata'
    time.tzset()
    dt = datetime.now().strftime('%d-%m-%Y')
    config = configparser.ConfigParser()
    config.read('district.cfg')
    district_ids = ast.literal_eval(config.get("District", "district_ids"))
    logging.debug('Checking For following District ids: %s', str(district_ids))
    for i in district_ids:
        try:
            result = json.dumps(get_covid_centers(i, dt), indent=4, sort_keys=True)
            logging.debug('Result for the district_id: %s Data dump is : %s', str(i), str(result))
            parse_data(result, dt)
            time.sleep(60)
        except Exception as e:
            logging.error('Obtained Exception while processing vaccine data: %s', str(e))
