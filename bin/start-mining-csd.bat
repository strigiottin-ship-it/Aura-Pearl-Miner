@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-gpu sha256d_csd --pool csd-eu.lproute.com:8760 --wallet csd-wallet
pause

