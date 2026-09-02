#!/bin/bash
# Test suite runner for agentic pipeline

echo "🧪 Agentic Pipeline Test Suite"
echo "=============================="
echo ""

# Create test output directory
mkdir -p test-results

# Test 1: Single person
echo "Test 1: Single Person Portrait"
if [ -f "test_images/portrait.jpg" ]; then
    python3 agentic_pipeline.py test_images/portrait.jpg -o test-results/test1
    echo "✓ Test 1 complete"
else
    echo "⚠️  Test 1 skipped (no test_images/portrait.jpg)"
fi
echo ""

# Test 2: Person with product
echo "Test 2: Person with Product"
if [ -f "test_images/endorsement.jpg" ]; then
    python3 agentic_pipeline.py test_images/endorsement.jpg -o test-results/test2
    echo "✓ Test 2 complete"
else
    echo "⚠️  Test 2 skipped (no test_images/endorsement.jpg)"
fi
echo ""

# Test 3: Group photo
echo "Test 3: Group Photo"
if [ -f "test_images/group.jpg" ]; then
    python3 agentic_pipeline.py test_images/group.jpg -o test-results/test3
    echo "✓ Test 3 complete"
else
    echo "⚠️  Test 3 skipped (no test_images/group.jpg)"
fi
echo ""

# Test 4: Products
echo "Test 4: Product Catalog"
if [ -f "test_images/products.jpg" ]; then
    python3 agentic_pipeline.py test_images/products.jpg -o test-results/test4
    echo "✓ Test 4 complete"
else
    echo "⚠️  Test 4 skipped (no test_images/products.jpg)"
fi
echo ""

# Test 5: Complex scene
echo "Test 5: Complex Scene"
if [ -f "test_images/complex.jpg" ]; then
    python3 agentic_pipeline.py test_images/complex.jpg -o test-results/test5
    echo "✓ Test 5 complete"
else
    echo "⚠️  Test 5 skipped (no test_images/complex.jpg)"
fi
echo ""

# Summary
echo "=============================="
echo "📊 Test Summary"
echo "=============================="
echo ""
echo "Results saved to: test-results/"
echo ""
echo "To review results:"
echo "  cat test-results/*/complete_analysis.json"
echo ""
echo "To check detections:"
echo "  grep 'detections_summary' test-results/*/*.json"
echo ""
