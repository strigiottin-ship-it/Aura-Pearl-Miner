@echo off
cd %~dp0
cls

SRBMiner-MULTI.exe --algorithm-cpu minotaurx --pool stratum.cryptopool.site:7020 --wallet LCC-wallet --password c=LCC
pause