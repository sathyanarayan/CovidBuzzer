# CovidBuzzer
To send SMS Notification on the Availability of the covid vaccine open slots for the week on a district

# General Architecture
![Screenshot 2021-05-03 at 2 02 47 PM](https://user-images.githubusercontent.com/14267192/116856203-5af30280-ac18-11eb-8df4-525bd0b42b3a.png)

# Automation Info 
* Currently the automation is scheduled to run on every 6 hours, but can be scheduled as per the convenience. A better servless structure would be to use aws lambda, cloudwatch to trigger. Considering the cost, and to run free tier, its scheduled to run from EC2 t2 mirco instances. 

* The users have to subscribe to respective respective districts sns topic, currently we have opened to only limited members as like to keep running with-in free tier.
