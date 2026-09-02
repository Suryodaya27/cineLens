# Pipeline Flow Diagram

## Complete Processing Pipeline

```mermaid
flowchart TD
    Start([Start]) --> Input[/"Input: Movie Name + Image"/]
    
    Input --> Stage1["<b>Stage 1: Actor & Object Detection</b><br/>updated_agentic_pipeline.py"]
    
    Stage1 --> S1P1["Face Detection & Recognition"]
    Stage1 --> S1P2["Object Detection (YOLOv8)"]
    Stage1 --> S1P3["Scene Analysis"]
    
    S1P1 --> S1Out["Output: Identified Actors<br/>+ Detected Objects<br/>+ Scene Context"]
    S1P2 --> S1Out
    S1P3 --> S1Out
    
    S1Out --> Stage2["<b>Stage 2: Actor Enrichment</b><br/>tmdb_enrichment.py"]
    
    Stage2 --> S2P1["Fetch Actor Profiles"]
    Stage2 --> S2P2["Get Latest Movies"]
    Stage2 --> S2P3["Retrieve Filmography"]
    
    S2P1 --> S2Out["Output: Actor Details<br/>+ Recent Movies<br/>+ Career Info"]
    S2P2 --> S2Out
    S2P3 --> S2Out
    
    S2Out --> Stage3["<b>Stage 3: Product Shopping</b><br/>unified_shopping.py"]
    
    Stage3 --> S3P1["Search Products Online"]
    Stage3 --> S3P2["Match Detected Objects"]
    Stage3 --> S3P3["Generate Shopping Links"]
    
    S3P1 --> S3Out["Output: Product Links<br/>+ Purchase Options<br/>+ Price Info"]
    S3P2 --> S3Out
    S3P3 --> S3Out
    
    S3Out --> End([End: Complete Results])
    
    style Stage1 fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    style Stage2 fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    style Stage3 fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px
    style Start fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style End fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Input fill:#fce4ec,stroke:#880e4f
    style S1Out fill:#e1f5ff,stroke:#01579b
    style S2Out fill:#f3e5f5,stroke:#4a148c
    style S3Out fill:#e8f5e9,stroke:#1b5e20
```

## Pipeline Summary

### Stage 1: Actor & Object Detection
**Script:** `updated_agentic_pipeline.py`
- **Input:** Movie name + Image frame
- **Process:** 
  - Face detection and actor identification
  - Object detection using YOLOv8
  - Scene context analysis
- **Output:** Identified actors, detected objects, scene metadata

### Stage 2: Actor Enrichment
**Script:** `tmdb_enrichment.py`
- **Input:** Identified actors from Stage 1
- **Process:**
  - Fetch actor profiles from TMDB
  - Retrieve latest movies and filmography
  - Gather career information
- **Output:** Enriched actor data with recent movies

### Stage 3: Product Shopping
**Script:** `unified_shopping.py`
- **Input:** Detected objects from Stage 1
- **Process:**
  - Search for products online
  - Match objects to purchasable items
  - Generate shopping links
- **Output:** Product links and purchase options

## Data Flow

```mermaid
graph LR
    A[Movie Frame] --> B[Stage 1]
    B --> C[Actors List]
    B --> D[Objects List]
    C --> E[Stage 2]
    E --> F[Actor Movies]
    D --> G[Stage 3]
    G --> H[Shopping Links]
    
    style A fill:#ffeb3b
    style C fill:#64b5f6
    style D fill:#64b5f6
    style F fill:#ba68c8
    style H fill:#81c784
```

## Execution Sequence

```bash
# Step 1: Detect actors and objects
python updated_agentic_pipeline.py --movie "Movie Name" --image "frame.jpg"

# Step 2: Enrich actor information
python tmdb_enrichment.py 

# Step 3: Find shopping links for detected objects
python unified_shopping.py 
```
