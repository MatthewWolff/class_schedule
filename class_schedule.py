#!/usr/bin/env python3

import fileinput
from datetime import datetime
from getpass import getpass
from time import sleep

from icalendar import Calendar, Event
from selenium import webdriver

cal = Calendar()
ical_name = '{}_schedule.ics'


def add_class_to_calendar(start_time, end_time, name, location, days):
    def make_event(start_date, count=14):
        start_datetime = datetime.strptime(start_date + ' ' + str(start_time), '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(start_date + ' ' + str(end_time), '%Y-%m-%d %H:%M')

        event_parameters = {
            'summary': name,
            'location': location,
            'dtstart': start_datetime,
            'dtend': end_datetime,
            'dtstamp': datetime.now(),
            'rrule': {'freq': 'weekly', 'count': count}
        }
        e = Event()
        [e.add(*param) for param in event_parameters.items()]
        cal.add_component(e)

    if 'M' in days: make_event(start_date='2019-09-09')
    if 'T' in days: make_event(start_date='2019-09-10')
    if 'W' in days: make_event(start_date='2019-09-04', count=15)
    if 'R' in days: make_event(start_date='2019-09-05')
    if 'F' in days: make_event(start_date='2019-09-06')


def amto24(timezone_time):
    hour_time = timezone_time.split(':')
    hour = int(hour_time[0])
    hour = hour + 12 if 'PM' in hour_time[1] and hour is not 12 else hour
    minute = hour_time[1][:2]
    return '{}:{}'.format(hour, minute)


def build_section_dict(class_name, section_data, location_dict):
    section_type, weekdays, times = section_data.replace(' - ', '-').split()  # remove spaces splitting
    start, end = times.split('-')
    name = class_name + ' ' + section_type

    section_dict = {
        'start_time': amto24(start),
        'end_time': amto24(end),
        'name': name,
        'location': location_dict[name],
        'days': weekdays,
    }
    return section_dict


def scrape_schedule(user, pw):
    with webdriver.Chrome() as browser:  # open Chrome instance via selenium
        # go to CSE schedule
        browser.get('https://enroll.wisc.edu/scheduler')

        # find the NetID/Username elements
        netID, password = browser.find_element_by_id('j_username'), browser.find_element_by_id('j_password')

        # login
        netID.send_keys(user)
        password.send_keys(pw.pop())  # send/delete password
        browser.find_element_by_name('_eventId_proceed').click()
        sleep(10)

        # Get class information with building/room location
        class_w_location = [c.text for c in browser.find_elements_by_class_name('fc-content')]

        # Get class information with days/times
        xpath = '//*[@id="scheduler-view"]/md-card[1]/md-content[1]/section[1]/md-list[2]/md-list-item[{}]/div[1]/div[2]/div[1]/div[1]'
        class_w_days = list()
        while len(browser.find_elements_by_xpath(xpath.format(len(class_w_days) + 1))) is not 0:
            class_w_days.append(browser.find_elements_by_xpath(xpath.format(len(class_w_days) + 1))[0].text)
    return class_w_days, class_w_location


def parse_class_data(class_sections, class_locs):
    # get only the relevant text for classes with days
    class_with_days_text = [cls for cls in class_sections if 'Online' not in cls]  # exclude online sections
    class_with_location_text = [cls.replace('check_circle', '') for cls in class_locs]

    # split up classes into a list of their attributes
    class_loc_2d = [classes.split('\n') for classes in class_with_location_text]
    class_day_2d = [classes.split('\n') for classes in class_with_days_text if 'Online section' not in classes]

    # store these attributes in dictionaries by class name
    c_section_info = dict((c[0], c[2:]) for c in class_day_2d)
    c_locations = dict((' '.join(c[1].split()[:-1]).replace('(', ''), c[2]) for c in class_loc_2d)

    return c_section_info, c_locations


if __name__ == '__main__':
    # acquire user credentials
    username = input('Enter your NetID: ')
    secret_password = [getpass()]  # store in list so we don't need to manually delete after one-time use

    # scrape info
    class_section_info, class_locations = parse_class_data(*scrape_schedule(username, secret_password))

    # build schedule
    class_list = list()
    for class_, sections in class_section_info.items():
        for section in sections:
            class_list.append(build_section_dict(class_, section, class_locations))

    # generate an icalendar from schedule
    [add_class_to_calendar(**class_) for class_ in class_list]

    # write icalendar
    with open(ical_name.format(username), 'wb') as schedule:
        schedule.write(cal.to_ical())

    # add reminders 15 min beforehand
    for line in fileinput.input(ical_name.format(username), inplace=True):
        print(line.rstrip().
              replace('END:VEVENT',
                      'BEGIN:VALARM\nACTION:DISPLAY\nDESCRIPTION:REMINDER\nTRIGGER:-PT15M\nEND:VALARM\nEND:VEVENT'))
