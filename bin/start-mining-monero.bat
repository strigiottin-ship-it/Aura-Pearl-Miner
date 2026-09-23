@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu randomx --pool de.monero.herominers.com:1111 --wallet monero-wallet
pause