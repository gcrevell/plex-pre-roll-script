import json
from plexapi.server import PlexServer
import requests
import re
import datetime
import holidays
from os import walk

def validateConfig(config):
	if 'plexInstance' not in config:
		raise ValueError('Plex url and token are required!')
	if 'url' not in config['plexInstance']:
		raise ValueError('Plex url is required!')
	if 'token' not in config['plexInstance']:
		raise ValueError('Plex token is required!')

	if 'groups' in config:
		for group in config['groups']:
			if 'startDate' not in group or 'endDate' not in group or 'path' not in group:
				raise ValueError('Each group of pre-roll videos must include a start and end date, and a path!')
			
def parseDate(date):
	pattern = re.compile("^(\d{2})\-(\d{2})$")

	if re.match(pattern, date):
		parsedDate = datetime.datetime.strptime(date, '%m-%d').date()
		parsedDate = parsedDate.replace(year=datetime.datetime.now().year)
	else:
		usHolidays = holidays.UnitedStates(years=datetime.datetime.now().year)
		parsedDate = usHolidays.get_named(date)[0]

	return parsedDate

def parseGroup(group):
	startDateString = group['startDate']
	endDateString = group['endDate']
	path = group['path']

	startOffsetDays = group.get('startDateOffsetDays', 0)
	endOffsetDays = group.get('endDateOffsetDays', 0)

	startDate = parseDate(startDateString)
	endDate = parseDate(endDateString)

	if endDate < startDate:
		endDate = endDate.replace(year=endDate.year + 1)

	startDate = startDate.replace(day=startDate.day + startOffsetDays)
	endDate = endDate.replace(day=endDate.day + endOffsetDays)

	now = datetime.datetime.now().date()

	if startDate < now and endDate > now:
		return path
	else:
		return None

def main():
	with open('config.json', 'r') as file:
		config = json.load(file)

		validateConfig(config)

	session = requests.Session()
	session.verify = False
	requests.packages.urllib3.disable_warnings()
	
	plex = PlexServer(config['plexInstance']['url'], config['plexInstance']['token'], session, timeout=None)
	
	useOverlappingGroups = config.get('useOverlappingGroups', False)

	paths = []

	if 'groups' in config:
		for group in config['groups']:
			path = parseGroup(group)
			if path is not None:
				paths.append(path)
				if not useOverlappingGroups:
					break
	
	if len(paths) == 0 and 'defaultPath' in config:
		paths.append(config['defaultPath'])

	prerolls = ''
	for path in paths:
		_, _, filenames = next(walk(path))
		for filename in filenames:
			prerolls = prerolls + path + '/' + filename + ';'

	plex.settings.get('cinemaTrailersPrerollID').set(prerolls)    
	plex.settings.save()

if __name__ == '__main__':
	main()
