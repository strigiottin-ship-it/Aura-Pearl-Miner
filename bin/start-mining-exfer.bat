@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu argon2id_exfer --pool exfer.luckypool.io:3335 --wallet exfer-wallet
pause
