#!/bin/sh
tail -f -n 500 scheduler.log | ./log-htmlify > ~/public_html/autogole/scheduler.log.html
