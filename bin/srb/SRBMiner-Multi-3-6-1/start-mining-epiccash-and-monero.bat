@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomepic --algorithm-cpu randomx --pool de.epicmine.io:3333 --pool xmrpool.eu:5555 --wallet epicmine-username --wallet monero-wallet --password m=pool --password x
pause