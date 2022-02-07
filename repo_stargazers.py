### Script to get GitHub profile data of all Stargazers of a given GitHub repository 
###
###	by Max Woolf (@minimaxir)

import json
import csv
import datetime
import time
import os
import urllib.request as urllib2
from urllib.error import HTTPError
import urllib.parse as urlparse
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv('.env')

access_token = os.environ.get('TOKEN')
repo = "deepchecks/deepchecks"

fields = ["name", "company", "location", "email", "linkedin_url", "github_url"]
page_number = 0
users_processed = 0
stars_remaining = True
list_stars = []

print("Gathering Stargazers for %s..." % repo)

###
###	This block of code creates a list of tuples in the form of (username, star_time)
###	for the Statgazers, which will later be used to extract full GitHub profile data
###

while stars_remaining:
	query_url = "https://api.github.com/repos/%s/stargazers?page=%s" % (repo, page_number)
	
	req = urllib2.Request(query_url)
	req.add_header('Accept', 'application/vnd.github.v3.star+json')
	req.add_header('Authorization', f'token {access_token}')
	try:
		response = urllib2.urlopen(req)
		print(response)
	except HTTPError as e:
		print(e)
		pass
	data = json.loads(response.read())
	
	for user in data:
		username = user['user']['login']
		
		star_time = datetime.datetime.strptime(user['starred_at'],'%Y-%m-%dT%H:%M:%SZ')
		star_time = star_time + datetime.timedelta(hours=-5) # EST
		star_time = star_time.strftime('%Y-%m-%d %H:%M:%S')
		
		list_stars.append((username, star_time))
		
	if len(data) < 25:
		stars_remaining = False
	
	page_number += 1

print("Done Gathering Stargazers for %s!" % repo)

list_stars = list(set(list_stars)) # remove dupes

print("Now Gathering Stargazers' GitHub Profiles...")

###
###	This block of code extracts the full profile data of the given Stargazer
###	and writes to CSV
###
		
with open('%s-stargazers.csv' % repo.split('/')[1], 'w') as stars:

	stars_writer = csv.writer(stars)
	stars_writer.writerow(fields)
	
	for user in list_stars:
		username = user[0]
	
		query_url = "https://api.github.com/users/%s" % (username)
		req = urllib2.Request(query_url)
		req.add_header('Accept', 'application/vnd.github.v3.star+json')
		req.add_header('Authorization', f'token {access_token}')
		try:
			response = urllib2.urlopen(req)
		except:
			pass
		data = json.loads(response.read())
		
		name = data['name'].strip()
		company = data['company'].strip()
		location = data['location']
		email = data['email']

		name_and_company = f'{name} {company}'
		linkedin_url = f'https://www.linkedin.com/search/results/all/?keywords={urlparse.quote(name_and_company)}'

		github_url = data['html_url']
		
		# created_at = datetime.datetime.strptime(data['created_at'],'%Y-%m-%dT%H:%M:%SZ')
		# created_at = created_at + datetime.timedelta(hours=-5) # EST
		# created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')
		
		stars_writer.writerow([name, company, location, email, linkedin_url, github_url])
		
		users_processed += 1
		
		if users_processed % 100 == 0:
			print("%s Users Processed: %s" % (users_processed, datetime.datetime.now()))
			
		time.sleep(1) # stay within API rate limit of 5000 requests / hour + buffer

###
### Upload csv to google sheet
###

SERVICE_ACCOUNT_FILE = 'keys.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DEEPCHECKS_SHEET_ID = '1vK4jcNI3lTRbMbAaBUfDcE5oPtQRFIHpu6MGqzWpstk'

creds = None
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('sheets', 'v4', credentials=creds)

sheet = service.spreadsheets()

with open('%s-stargazers.csv' % repo.split('/')[1], 'r') as csv_file:
	csvContents = csv_file.read()
body = {
	'requests': [{
		'pasteData': {
			"coordinate": {
				"sheetId": DEEPCHECKS_SHEET_ID,
				"rowIndex": "0",  # adapt this if you need different positioning
				"columnIndex": "0", # adapt this if you need different positioning
			},
			"data": csvContents,
			"type": 'PASTE_NORMAL',
			"delimiter": ',',
		}
	}]
}
response = sheet.values().batchUpdate(spreadsheetId=DEEPCHECKS_SHEET_ID, body=body).execute()