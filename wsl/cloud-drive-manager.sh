#!/bin/bash
cd ~/cloud-drive
exec env PYTHONPATH=src python3 -m src.main --prod
