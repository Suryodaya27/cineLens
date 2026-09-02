#!/bin/bash

echo "=========================================="
echo "Testing Visual Search Integration"
echo "=========================================="
echo ""

# Test with existing analysis file
echo "Running visual search on morgan_complete_analysis.json..."
echo ""

python3 visual_search.py final-output/morgan_complete_analysis.json

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Check output file: final-output/morgan_complete_analysis_with_visual_search.json"
