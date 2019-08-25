import os
import semver

with open('git-tag') as f:
  git_tag = f.readline()

try:
  ver = semver.parse(git_tag)
except:
  ver = False


if ver:
  print('prod!')
