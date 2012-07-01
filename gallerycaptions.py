#!/usr/bin/python

# This is a utility for taking photos that have been hosted in Gallery2 and
# writing the description and caption data into IPTC fields that can be read
# by Picasa or other photo managers.

# Written for pyexiv2 0.3.2.

# Run the command in the same directory as a local copy of the g2data/albums
# folder. The arguments are the CSV files containing the data from the gallery
# database.

# $ ../gallerycaptions/gallerycaptions.py \
#     ../item.csv ../child_entity.csv ../filesystem_entity.csv

# Commands to export gallery data from MySQL:
# select * from g2_FileSystemEntity into outfile '/tmp/filesystem_entity.csv' \
#   fields terminated by ',' optionally enclosed by '"' escaped by '\\' \
#   lines terminated by '\n';
# select * from g2_Item into outfile '/tmp/item.csv' \
#   fields terminated by ',' optionally enclosed by '"' escaped by '\\' \
#   lines terminated by '\n';
# select * from g2_ChildEntity into outfile '/tmp/child_entity.csv' \
#   fields terminated by ',' optionally enclosed by '"' escaped by '\\' \
#   lines terminated by '\n';

# For reference, here's the schema of the tables exported above.
# mysql> describe g2_Item;
# +------------------------+--------------+------+-----+---------+-------+
# | Field                  | Type         | Null | Key | Default | Extra |
# +------------------------+--------------+------+-----+---------+-------+
# | g_id                   | int(11)      | NO   | PRI | 0       |       |
# | g_canContainChildren   | int(1)       | NO   |     | 0       |       |
# | g_description          | text         | YES  |     | NULL    |       |
# | g_keywords             | varchar(255) | YES  | MUL | NULL    |       |
# | g_ownerId              | int(11)      | NO   | MUL | 0       |       |
# | g_summary              | varchar(255) | YES  | MUL | NULL    |       |
# | g_title                | varchar(128) | YES  | MUL | NULL    |       |
# | g_viewedSinceTimestamp | int(11)      | NO   |     | 0       |       |
# | g_originationTimestamp | int(11)      | NO   |     | 0       |       |
# | g_renderer             | varchar(128) | YES  |     | NULL    |       |
# +------------------------+--------------+------+-----+---------+-------+
# 
# mysql> describe g2_FileSystemEntity;
# +-----------------+--------------+------+-----+---------+-------+
# | Field           | Type         | Null | Key | Default | Extra |
# +-----------------+--------------+------+-----+---------+-------+
# | g_id            | int(11)      | NO   | PRI | 0       |       |
# | g_pathComponent | varchar(128) | YES  | MUL | NULL    |       |
# +-----------------+--------------+------+-----+---------+-------+
# 
# mysql> describe g2_ChildEntity;
# +------------+---------+------+-----+---------+-------+
# | Field      | Type    | Null | Key | Default | Extra |
# +------------+---------+------+-----+---------+-------+
# | g_id       | int(11) | NO   | PRI | 0       |       |
# | g_parentId | int(11) | NO   | MUL | 0       |       |
# +------------+---------+------+-----+---------+-------+

import csv
import os.path
import pyexiv2
import sys

IPTC_KEY = 'Iptc.Application2.Caption'

itemFile = sys.argv[1]
childEntityFile = sys.argv[2]
filesystemEntityFile = sys.argv[3]

print 'item file: ' + itemFile
print 'child entity file: ' + childEntityFile
print 'filesystem entity file: ' + filesystemEntityFile

items = {}
for row in csv.reader(open(itemFile)):
  # Find the unique text from the description, summary, and title
  # Remove '\\N' which represents NULL in MySQL and empty strings
  # Sort from shortest to longest
  # Join with ' - '
  text = set([row[2], row[5], row[6]])
  text.discard('\\N')
  text.discard('')
  items[row[0]] = ' - '.join(sorted(text, key=len))

childEntities = {}
for row in csv.reader(open(childEntityFile)):
  childEntities[row[0]] = row[1]

filesystemEntities = {}
for row in csv.reader(open(filesystemEntityFile)):
  filesystemEntities[row[0]] = row[1]

fileCaptions = {}
for id, caption in items.iteritems():
  path = []
  pathId = id
  while filesystemEntities[pathId] != '\\N':
    path.insert(0, filesystemEntities[pathId])
    if pathId not in childEntities:
      break
    pathId = childEntities[pathId]
  if len(path) == 0:
    continue
  fileCaptions[os.path.join(*path)] = caption

for path, caption in fileCaptions.iteritems():
  if not os.path.isfile(path):
    continue

  metadata = pyexiv2.ImageMetadata(path)
  metadata.read()

  # Preserve any existing caption.
  if IPTC_KEY in metadata.iptc_keys:
    caption = ' - '.join(metadata[IPTC_KEY].value + [caption])

  metadata[IPTC_KEY] = pyexiv2.IptcTag(IPTC_KEY, [caption])

  print path + ': ' + metadata[IPTC_KEY].value[0]
  metadata.write(preserve_timestamps=True)
