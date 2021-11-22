# -*- coding: utf-8 -*-
"""
Created on Mon Nov 22 20:20:56 2021

@author: tobycrisford
"""

import subprocess, sys
import os

#Export necessary request using chrome developer tools - save in powershell_request.txt
with open("powershell_request.txt", "r") as f:
    ps_req = f.readlines()

ps_req[-1] = ps_req[-1] + ' -OutFile "compressed_json.br"'

#Edit request to fetch 10,000 activities
for i in range(len(ps_req)):
    limit_index = ps_req[i].find('?limit=')
    start_index = ps_req[i].find('&start=')
    if limit_index != -1:
        ps_req[i] = ps_req[i][:limit_index] + '?limit=10000&start=0' + ps_req[i][start_index+9:]

with open("powershell_request.ps1", "w") as f_out:
    f_out.writelines(ps_req)
    
p = subprocess.Popen('powershell.exe -ExecutionPolicy RemoteSigned -file "powershell_request.ps1"')

print("Fetched data")

os.system("del activity_data.json")

os.system('Brotli.exe --decompress --in compressed_json.br --out activity_data.json')

print("Decompressed")