# Implementation

- periodic sharder syncs
  - paginated lists
  - otherwise, memory consumption would spike proportional to number of objects during syncs
  - also reduces load on API server
