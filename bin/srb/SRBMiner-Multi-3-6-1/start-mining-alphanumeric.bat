@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu blake3_an --pool eu.lproute.com:4260 --wallet alphanumeric-wallet
pause

