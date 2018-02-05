#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Toggl to Zoho Invoice connector

Sync time entries from Toggl to Zoho Invoice (EU)
"""

# workaround to help Lambda find the packages and not clutter the project root
import sys
sys.path.insert(0, './env/lib/python3.6/site-packages')

import configparser
import logging
import json

import arrow
import requests
import tapioca_toggl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TOGGL')

config = configparser.RawConfigParser()
config.read('config.ini')

logger.debug('Reading auth from user config')
toggl = tapioca_toggl.Toggl(access_token=config.get('Toggl', 'access_token'))


def add_zoho_entry(tte):
    """Submit toggl time entry to Zoho Invoice"""

    params = {
        'authtoken': config.get('Zoho', 'api_key'),
        'organization_id': config.get('Zoho', 'org_id'),
    }

    if 'pid' not in tte:
        logger.warning('Ignoring timecard without project')
        return False

    try:
        mapping = config.get('Mapping', str(tte['pid']))
    except configparser.NoOptionError:
        logger.warning('Ignoring timecard %s due to missing config', tte['pid'])
        return False

    (zoho_project_id, zoho_task_id) = mapping.split(':')
    if not zoho_project_id or not zoho_task_id:
        logger.warning('Could not map IDs for project %s', tte['pid'])
        return False

    start_date = arrow.get(tte['start']).to('Europe/Berlin')
    end_date = arrow.get(tte['stop']).to('Europe/Berlin')

    if not start_date.date() == end_date.date():
        logger.warning("Cannot handle time entries spanning multiple days!")
        return False

    data = {
        'project_id': zoho_project_id,
        'task_id': zoho_task_id,
        'user_id': config.get('Zoho', 'user_id'),
        'log_date': start_date.format('YYYY-MM-DD'),
        'begin_time': start_date.format('HH:mm'),
        'end_time': end_date.format('HH:mm'),
        'notes': str(tte['id'])
    }

    logger.info("Adding timecard with TTE ID %s to Zoho", tte['id'])
    jsonstring = {'JSONString': json.dumps(data)}
    req = requests.post('https://invoice.zoho.eu/api/v3/projects/timeentries', params=params, data=jsonstring)
    req.raise_for_status()
    return True


def get_toggl_time_entries(start_date, end_date):
    """Get all time entries for a given time period from Toggl"""
    time_entries = toggl.time_entries().get(
        params={
            'start_date': start_date.format('YYYY-MM-DDTHH:mm:ssZZ'),
            'end_date': end_date.format('YYYY-MM-DDTHH:mm:ssZZ'),
        }
    )
    return time_entries().data


def get_zoho_time_entries(start_date, end_date):
    """Get all time entries for a given time period from Zoho"""
    params = {
        'authtoken': config.get('Zoho', 'api_key'),
        'organization_id': config.get('Zoho', 'org_id'),
        'filter_by': 'Date.CustomDate',
        'from_date': start_date.format('YYYY-MM-DD'),
        'to_date': end_date.format('YYYY-MM-DD')
    }
    req = requests.get('https://invoice.zoho.eu/api/v3/projects/timeentries', params=params)
    return req.json()['time_entries']


def find_zoho_entry(toggl_time_entry, zoho_time_entries):
    """Find Zoho entry for a given Toggl entry"""
    tte_id = str(toggl_time_entry['id'])

    for zte in zoho_time_entries:
        if zte['notes'] == tte_id:
            logger.info('Found matching ZTE ID %s for TTE ID %s' % (zte['time_entry_id'], tte_id))
            return True

    logger.info('Found no matching ZTE for TTE ID %s' % tte_id)
    return False


def notify_ifttt(synced_entries, failed_entries):
    """Send notification to IFTTT about synced and failed timecards"""
    maker_key = config.get('IFTTT', 'maker_key')
    if maker_key:
        body = {}
        body["value1"] = str(synced_entries)
        body["value2"] = str(failed_entries)
        req = requests.post('https://maker.ifttt.com/trigger/toggl_timesync/with/key/'+maker_key, json=body)
        req.raise_for_status()


def main():
    """ Main entry point of the app """

    synced_entries = 0
    failed_entries = 0

    logger.debug('Retrieving user data')
    me = toggl.me_with_related_data().get()

    toggl_tz = me.data.timezone().data
    logger.debug('Timezone set to %s' % toggl_tz)

    start_sync = arrow.utcnow().shift(days=-7).to(toggl_tz)
    end_sync = arrow.utcnow().shift(days=0).to(toggl_tz)
    logger.info('Sync from %s until %s' % (start_sync.format('YYYY-MM-DDTHH:mm:ssZZ'), end_sync.format('YYYY-MM-DDTHH:mm:ssZZ')))

    toggl_time_entries = get_toggl_time_entries(start_sync, end_sync)
    logger.info('Found %d time entries in Toggl for the last 7 days', len(toggl_time_entries))
    zoho_time_entries = get_zoho_time_entries(start_sync, end_sync)
    logger.info('Found %d time entries in Zoho for the last 7 days', len(zoho_time_entries))

    for tte in toggl_time_entries:
        if not find_zoho_entry(tte, zoho_time_entries):
            result = add_zoho_entry(tte)
            if result:
                synced_entries += 1
            else:
                failed_entries += 1

    notify_ifttt(synced_entries, failed_entries)


def run(event, context):
    """This is executed by AWS Lambda"""
    main()
    return {
        "message": "Toggl to Zoho sync ran successfully",
        "event": event
    }


if __name__ == "__main__":
    """This is executed when run from the command line"""
    main()
