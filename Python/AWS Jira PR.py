"""
AWS Jira data sync
Author: Jeremy Herbert
Date: Approx Sept 2023

This script is an AWS Lambda function that tracks pull requests (pr) made in AWS CodeCommit and updates the correspondent Jira ticket.
The Lambda function does the following:
1. Tracks the AWS Eventbridge events, and filter for PRs
2. Collects the PRs' CodeCommit link
3a. Checks if there are any previous PR URLs in the Jira ticket
3b. If there is a previous PR URL, copy the previous PR URLs/info, append the new URL to the list, and send the data to the Jira ticket via the Jira API.
3c. If there is no previous PR URL, send the data to the Jira ticket via the Jira API.
"""


import json, os, re, urllib3
from urllib3.util import make_headers


JIRA_URL = os.environ['JIRA_URL']
JIRA_API_TOKEN = os.environ['JIRA_API_TOKEN']
JIRA_EMAIL = os.environ['JIRA_EMAIL']


def lambda_handler(event,context):
    # Extract the pull request information from the event
    s1 = json.dumps(event)
    d2 = json.loads(s1)
    print(d2)
    
    #Confirm that a pull request was created, not merged:
    if d2['detail']['event'] == 'pullRequestCreated':
        pr_url = re.findall("(?<= CodeCommit console ).+(?=\.)", d2['detail']['notificationBody'])[0]
        pr_id = d2['detail']['pullRequestId']
        pr_repo = d2['detail']['repositoryNames'][0]

        # Extract the Jira ticket ID from the pull request title
        mea_pattern = r"^MEA-\d{4,}"
        jira_ticket_id = (re.match(mea_pattern, d2['detail']['title'])).group()

        # Update the labels of the Jira ticket
        update_jira_ticket_labels(jira_ticket_id, pr_url, pr_id, pr_repo)


def update_jira_ticket_labels(jira_ticket_id, PR_URL, PR_ID, PR_REPO):
    # Set the URL for the Jira API endpoint
    url = f"{JIRA_URL}/rest/api/3/issue/{jira_ticket_id}"

    # Set the headers for the API request
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    http = urllib3.PoolManager()
    basic_auth = make_headers(basic_auth=f'{JIRA_EMAIL}:{JIRA_API_TOKEN}')
    headers.update(basic_auth)

    # Make an API request to retrieve the current value of the custom field
    response = http.request('GET', url, headers=headers)

    # Check if the request was successful
    if response.status == 200:

        # Parse the JSON response
        issue_data = json.loads(response.data.decode('utf-8'))

        # Retrieve the current value of the custom field

        if issue_data['fields']['customfield_10051']:
            current_custom_field_value = issue_data['fields']['customfield_10051']['content']
            # Find the existing ordered list within the ADF data:
            ordered_list = next((item for item in current_custom_field_value if item['type'] == 'orderedList'), None)
        else:
            current_custom_field_value = []
            ordered_list = None
        
        # Check if an ordered list was found
        if ordered_list:
            # Append the new item to the content of the ordered list
            ordered_list['content'].append({
                "type": "listItem",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": f"{PR_REPO} | {PR_ID}",
                                "marks": [
                                    {
                                        "type": "link",
                                        "attrs": {
                                            "href": PR_URL
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            })
        else:
            # Create a new ordered list with the new item as its first element
            current_custom_field_value.append({
                "type": "orderedList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"{PR_REPO} | {PR_ID}",
                                        "marks": [
                                            {
                                                "type": "link",
                                                "attrs": {
                                                    "href": PR_URL
                                                }
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            })

        # Set the data for the API request in Atlassian Data Format (ADF)
        adf_document = {
            "version": 1,
            "type": "doc",
            "content": current_custom_field_value
        }

        data = {
            'fields': {
                'customfield_10051': adf_document
            }
        }

        # Make an API request to update the custom field with the new value
        response = http.request('PUT', url, headers=headers, body=json.dumps(data))

        # Check if the API request was successful
        if response.status == 204:
        # if response.status_code == 204:
            print(f"Successfully updated labels of Jira ticket {jira_ticket_id}")
        else:
            print(f"ERROR, Failed to update labels of Jira ticket {jira_ticket_id}")
    else:
        print(f"ERROR: Failed to retrieve data for Jira ticket {jira_ticket_id}. Status code: {response.status}")
        print(f"Response content: {response.content}")
