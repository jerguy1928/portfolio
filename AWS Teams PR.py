"""
AWS Teams Notifications
Author: Jeremy Herbert
Date: Approx Mar 2023

This script is an AWS Lambda function that tracks pull requests (pr) made and merged in AWS CodeCommit and sends a message in Microsoft Teams to facilitate code review.
The message is sent to a Teams channel in Microsoft Teams via a webhook.
The Lambda function does the following:
1. Tracks the AWS Eventbridge events, and filter for PRs
2. Collects the PRs' relevant information like the author, the repo, etc.
3. The PR information is posted to the webhook
4. The webhook fires and a message is displayed to developers in Microsoft Teams.
"""
import json, os, re, urllib.request


#Lambda function gets the events from Code Commit, and performs regex to determine if the CodeCommit message is a PR
def lambda_handler(event, context):
    s1 = json.dumps(event)
    d2 = json.loads(s1)
    pr_author = re.findall("[^\/]+$",d2['detail']['author'])[0]
    pr_merger = re.findall("[^\/]+$",d2['detail']['callerUserArn'])[0]
    pr_url = re.findall("(?<= CodeCommit console ).+", d2['detail']['notificationBody'])[0]
    
    #if there is a new PR, create the PR creation message
    if d2['detail']['event'] == 'pullRequestCreated':
        message = {'text': f'''A pull request has been created. <br> 
PR Author: {pr_author} <br>
PR Title: {d2['detail']['title']} <br>
PR Repo: {d2['detail']['repositoryNames'][0]} <br>
Destination Branch: {d2['detail']['destinationReference']} <br>
PR ID: {d2['detail']['pullRequestId']} <br>
PR URL: {pr_url}'''}
    
    #if there is a merged PR, create the PR merged message
    elif d2['detail']['event'] == 'pullRequestMergeStatusUpdated':
        message = {'text': f'''The pull request has been merged. <br>
PR Author: {pr_author} <br>
PR Merger: {pr_merger} <br>
PR Title: {d2['detail']['title']} <br>
PR Repo: {d2['detail']['repositoryNames'][0]} <br>
Destination Branch: {d2['detail']['destinationReference']} <br>
PR ID: {d2['detail']['pullRequestId']} <br>
PR URL: {pr_url}'''}
    
    #create the request to be posted to the webhook
    data = json.dumps(message).encode('ascii')
    req = urllib.request.Request(os.environ['teams_real'],
                             data=data, 
                             headers={'content-type': 'application/json'})

    try:
        response = urllib.request.urlopen(req)
        response.read()
    except Exception as e:
        print (e)
        raise e