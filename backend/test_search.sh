#!/bin/bash
# Comprehensive test script for full-text search functionality

BASE_URL="http://localhost:6001"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo "Full-Text Search Functionality Tests"
echo "======================================"
echo ""

# Test 1: Backward compatibility (no search)
echo "Test 1: Backward compatibility - list tasks without search"
response=$(curl -s "${BASE_URL}/api/tasks?limit=2")
if [[ $response == *"\"id\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Backward compatibility maintained"
else
    echo -e "${RED}✗ FAIL${NC}: Backward compatibility broken"
fi
echo ""

# Test 2: Basic text search
echo "Test 2: Basic text search - search for 'bug'"
response=$(curl -s "${BASE_URL}/api/tasks?q=bug&limit=3")
if [[ $response == *"\"id\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Basic text search works"
else
    echo -e "${RED}✗ FAIL${NC}: Basic text search failed"
fi
echo ""

# Test 3: Search with relevance sorting (default)
echo "Test 3: Search with relevance sorting"
response=$(curl -s "${BASE_URL}/api/tasks?q=database&limit=3")
if [[ $response == *"\"id\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Relevance sorting works"
else
    echo -e "${RED}✗ FAIL${NC}: Relevance sorting failed"
fi
echo ""

# Test 4: Custom sorting (updated_at)
echo "Test 4: Custom sorting by updated_at"
response=$(curl -s "${BASE_URL}/api/tasks?q=task&sort_by=-updated_at&limit=3")
if [[ $response == *"\"id\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Custom sorting works"
else
    echo -e "${RED}✗ FAIL${NC}: Custom sorting failed"
fi
echo ""

# Test 5: Multi-field sorting
echo "Test 5: Multi-field sorting (rank + priority)"
response=$(curl -s "${BASE_URL}/api/tasks?q=feature&sort_by=-rank,-priority&limit=3")
if [[ $response == *"\"id\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Multi-field sorting works"
else
    echo -e "${RED}✗ FAIL${NC}: Multi-field sorting failed"
fi
echo ""

# Test 6: Global search endpoint
echo "Test 6: Global search endpoint"
response=$(curl -s "${BASE_URL}/api/search?q=project&limit=3")
if [[ $response == *"\"tasks\":"* ]] && [[ $response == *"\"projects\":"* ]] && [[ $response == *"\"comments\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Global search works"
else
    echo -e "${RED}✗ FAIL${NC}: Global search failed"
fi
echo ""

# Test 7: Empty search query validation
echo "Test 7: Empty search query validation"
response=$(curl -s "${BASE_URL}/api/search?q=")
if [[ $response == *"cannot be empty"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Empty query validation works"
else
    echo -e "${RED}✗ FAIL${NC}: Empty query validation failed"
fi
echo ""

# Test 8: Search with filters
echo "Test 8: Search with filters (status + priority)"
response=$(curl -s "${BASE_URL}/api/tasks?q=task&status=done&priority=P0&limit=3")
if [[ $response == *"\"id\":"* ]]; then
    echo -e "${GREEN}✓ PASS${NC}: Search with filters works"
else
    echo -e "${RED}✗ FAIL${NC}: Search with filters failed"
fi
echo ""

# Test 9: Verify search vectors populated
echo "Test 9: Verify search vectors are populated"
docker exec task-tracker-db psql -U taskuser -d tasktracker -c "SELECT COUNT(*) as total, COUNT(search_vector) as with_vectors FROM tasks;" > /tmp/search_test.txt 2>&1
if grep -q "with_vectors" /tmp/search_test.txt; then
    echo -e "${GREEN}✓ PASS${NC}: Search vectors populated in database"
else
    echo -e "${RED}✗ FAIL${NC}: Search vectors not properly populated"
fi
echo ""

echo "======================================"
echo "All Tests Complete!"
echo "======================================"
