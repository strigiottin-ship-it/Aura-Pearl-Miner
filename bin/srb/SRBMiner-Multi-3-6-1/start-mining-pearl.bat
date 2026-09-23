@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu pearlhash --pool prl.kryptex.network:7048,de.pearl.herominers.com:1200,pearl-eu2.luckypool.io:3360 --wallet prl-wallet --worker prl-worker
pause

