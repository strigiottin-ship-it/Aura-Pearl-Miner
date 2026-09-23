@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomepic --pool de.epicmine.io:3333 --wallet epicmine-username --password m=pool --algorithm-cpu xelishashv3 --pool xel.suprnova.cc:3333 --wallet xelis-wallet --password x
pause