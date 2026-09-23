@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu sha3t --pool btc3forge.com:3337 --wallet btc3-wallet
pause

