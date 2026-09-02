# Test Cases for Agentic Pipeline

## Test Case 1: Single Person Portrait
**Image**: Person headshot, no objects
**Expected Output**:
```json
{
  "people": [{
    "name": "Actor Name" or null,
    "facial_features": "...",
    "clothing": "...",
    "held_items": null
  }]
}
```
**Command**: `python3 agentic_pipeline.py portrait.jpg`

---

## Test Case 2: Person with Product (Endorsement)
**Image**: Actor holding Pepsi/Coke bottle
**Expected Output**:
```json
{
  "people": [{
    "name": "Actor Name",
    "held_items": "Pepsi bottle"
  }],
  "products": [{
    "brand": "Pepsi",
    "product_type": "soda"
  }]
}
```
**Command**: `python3 agentic_pipeline.py endorsement.jpg`

---

## Test Case 3: Person with Undetected Object
**Image**: Person holding guitar (YOLO might miss it)
**Expected Output**:
```json
{
  "people": [{
    "name": "Musician Name",
    "held_items": "acoustic guitar",
    "clothing": "..."
  }]
}
```
**Note**: Even if YOLO doesn't detect guitar as separate object, vision model should mention it in `held_items`

**Command**: `python3 agentic_pipeline.py musician.jpg`

---

## Test Case 4: Group Photo
**Image**: Multiple people (3-5 people)
**Expected Output**:
```json
{
  "people": [
    {"name": "Person 1", "clothing": "..."},
    {"name": "Person 2", "clothing": "..."},
    {"name": "Person 3", "clothing": "..."}
  ]
}
```
**Command**: `python3 agentic_pipeline.py group.jpg`
**With Parallel**: `python3 agentic_pipeline.py group.jpg --parallel`

---

## Test Case 5: Product Catalog
**Image**: Multiple bottles/products on table
**Expected Output**:
```json
{
  "products": [
    {"brand": "Coca-Cola", "product_type": "soda"},
    {"brand": "Pepsi", "product_type": "soda"},
    {"brand": "Sprite", "product_type": "soda"}
  ]
}
```
**Command**: `python3 agentic_pipeline.py products.jpg`

---

## Test Case 6: Event/Party Scene
**Image**: People with drinks, furniture visible
**Expected Output**:
```json
{
  "scene_analysis": {
    "setting": "Indoor party/event",
    "lighting": "..."
  },
  "people": [...],
  "products": [...],
  "furniture": [...]
}
```
**Command**: `python3 agentic_pipeline.py party.jpg`

---

## Test Case 7: Street Scene with Vehicles
**Image**: People and cars on street
**Expected Output**:
```json
{
  "people": [...],
  "vehicles": [
    {"make": "Toyota", "model": "Camry", "color": "silver"}
  ]
}
```
**Command**: `python3 agentic_pipeline.py street.jpg`

---

## Test Case 8: Pet Photo
**Image**: Dog or cat
**Expected Output**:
```json
{
  "animals": [{
    "breed": "Golden Retriever",
    "color": "golden",
    "activity": "sitting"
  }]
}
```
**Command**: `python3 agentic_pipeline.py pet.jpg`

---

## Test Case 9: Electronics Setup
**Image**: Laptop, phone, keyboard on desk
**Expected Output**:
```json
{
  "electronics": [
    {"brand": "Apple", "model": "MacBook Pro"},
    {"brand": "Apple", "model": "iPhone 15"}
  ]
}
```
**Command**: `python3 agentic_pipeline.py desk.jpg`

---

## Test Case 10: Complex Scene
**Image**: Person holding phone, with laptop on table, car in background
**Expected Output**:
```json
{
  "people": [{
    "held_items": "smartphone"
  }],
  "electronics": [
    {"brand": "...", "model": "smartphone"},
    {"brand": "...", "model": "laptop"}
  ],
  "vehicles": [...]
}
```
**Command**: `python3 agentic_pipeline.py complex.jpg`

---

## Known Limitations

### YOLO Detection Limits
YOLO can detect 80 classes, but might miss:
- Musical instruments (guitar, piano, drums)
- Sports equipment (tennis racket, baseball bat - some supported)
- Small accessories (jewelry, watches - except clock class)
- Food items (only common ones like pizza, banana, apple)

**Workaround**: Vision model will still mention these in:
- `held_items` field for people
- Scene analysis context

### When Objects Are Missed
If YOLO doesn't detect an object but it's visible:
1. Check `people[].held_items` - vision model describes what person holds
2. Check `scene_analysis.background_elements` - might be mentioned there
3. Consider using better YOLO model: `--yolo-model yolov8m.pt` or `yolov8x.pt`

---

## Testing Workflow

### 1. Quick Test (Single Image)
```bash
python3 agentic_pipeline.py test_image.jpg
cat final-output/test_image_complete_analysis.json
```

### 2. Batch Test (Multiple Images)
```bash
for img in test_images/*.jpg; do
  python3 agentic_pipeline.py "$img"
done
```

### 3. Compare Results
```bash
# Check what was detected
grep -A 5 "detections_summary" final-output/*.json

# Check people identified
grep -A 3 '"name"' final-output/*.json

# Check products found
grep -A 3 '"brand"' final-output/*.json
```

---

## Success Criteria

✅ **Pass**: Detects main subjects (people, obvious products)
✅ **Pass**: Identifies celebrities/actors when visible
✅ **Pass**: Describes held items even if not detected separately
✅ **Pass**: Provides scene context
✅ **Pass**: Structured JSON output

⚠️ **Acceptable**: Misses small/obscured objects
⚠️ **Acceptable**: Can't identify unknown people
⚠️ **Acceptable**: Misses objects outside YOLO's 80 classes

❌ **Fail**: Doesn't detect obvious people
❌ **Fail**: Doesn't detect clear products (bottles, phones)
❌ **Fail**: JSON parsing errors
❌ **Fail**: Crashes or hangs

---

## Recommended Test Images

1. **Celebrity with product**: Actor holding branded item
2. **Group photo**: 3-5 people together
3. **Product shot**: Multiple bottles/items
4. **Street scene**: People + cars
5. **Pet photo**: Dog or cat
6. **Desk setup**: Laptop + phone + accessories
7. **Party/event**: People + drinks + furniture
8. **Sports**: Person with equipment
9. **Music**: Person with instrument
10. **Complex**: Multiple categories in one image

---

## Performance Benchmarks

| Scenario | Objects | Time (sequential) | Time (parallel) |
|----------|---------|-------------------|-----------------|
| Single person | 1 | ~5-8s | ~5-8s |
| Person + product | 2 | ~10-15s | ~10-15s |
| Group (5 people) | 5 | ~30-40s | ~15-20s |
| Complex (10+ objects) | 10+ | ~60-90s | ~25-35s |

*Times vary based on vision model and hardware*

---

## Tips for Best Results

1. **Good lighting**: Better detection and analysis
2. **Clear subjects**: Not too far or obscured
3. **High resolution**: Better for small objects
4. **Use better YOLO**: `yolov8m.pt` for more detections
5. **Check held_items**: Even if object not detected separately
6. **Review crops**: Visual confirmation of what was detected
