#!/usr/bin/env bash

curl -F "url=${WEB_HOOK}" -F "certificate=@${PATH_TO_CERT}" https://api.telegram.org/bot${BOT_TOKEN}/setwebhook
