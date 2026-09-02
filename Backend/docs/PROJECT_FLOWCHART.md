# AI-Powered Movie Analysis & Product Discovery System - Flowchart

## System Architecture Flow

```mermaid
flowchart TD
    A[User Input] --> B{Input Type}
    B -->|Upload Image| C[Frontend: Store in Object Storage]
    B -->|EPG Coverage| D[Get Movie Name + Image URL]
    
    C --> E[Get Object Storage Link]
    D --> F[Movie Name + Image URL]
    E --> F
    
    F --> G{Enable Vision?}
    
    %% Without Vision Path
    G -->|No| H[Standard Processing Mode]
    H --> I[Query TMDB API with Movie Name]
    I --> J[Get TMDB Movie ID]
    J --> K[Fetch Cast Information]
    K --> L[Download 3-5 Images per Actor]
    L --> M[Convert Actor Images to Embeddings]
    M --> N[Store Embeddings in PostgreSQL]
    
    N --> O[Process User Image with YOLO]
    O --> P[Crop Detected People/Objects]
    P --> Q[Convert Cropped Faces to Embeddings]
    Q --> R[Compare with Stored Embeddings]
    R --> S{Match > Threshold?}
    S -->|Yes| T[Identify Actor]
    S -->|No| U[Unknown Person]
    
    T --> V[Display Results in Frontend UI]
    U --> V
    
    %% With Vision Path
    G -->|Yes| W[Vision-Enhanced Mode]
    W --> X[Execute Standard Processing]
    X --> Y[Actor Identified]
    Y --> Z[Analyze Scene with Ollama Qwen Vision]
    
    Z --> AA[Scene Analysis]
    Z --> BB[Actor Analysis - Clothes, Pose, Objects]
    Z --> CC[Object Detection & Analysis]
    
    AA --> DD[Compile Vision Results]
    BB --> DD
    CC --> DD
    
    DD --> EE[Enhanced Results with Scene Context]
    
    %% Additional Features
    V --> FF[Get More Movies of Same Actor]
    EE --> FF
    
    FF --> GG[TMDB API: Fetch Actor's Filmography]
    GG --> HH[Display Actor's Other Movies]
    
    %% Monetization Features
    HH --> II[Product Discovery Pipeline]
    II --> JJ[Amazon Scraping for Actor's Clothing]
    II --> KK[SerpAPI Reverse Image Search for Products]
    
    JJ --> LL[Generate Shopping Links]
    KK --> LL
    
    LL --> MM[Cache Results]
    MM --> NN[Display Final Results with Shopping Options]
    
    %% Database
    OO[(PostgreSQL Database)] --> N
    OO --> R
    
    %% External APIs
    PP[TMDB API] --> I
    QQ[Amazon Scraper] --> JJ
    RR[SerpAPI] --> KK
    SS[Ollama Qwen Vision] --> Z
    
    style A fill:#e1f5fe
    style NN fill:#c8e6c9
    style G fill:#fff3e0
    style II fill:#f3e5f5
```

## Key Components Breakdown

### 1. Input Processing
- **Frontend**: Next.js application handles image uploads
- **Object Storage**: Secure image storage with URL generation
- **EPG Integration**: Automatic movie/series detection

### 2. Core Pipeline Modes

#### Standard Mode (Without Vision)
1. **TMDB Integration**: Movie metadata and cast information
2. **Embedding Generation**: Face recognition using embeddings
3. **YOLO Processing**: Object and person detection
4. **Actor Matching**: Threshold-based identification

#### Vision-Enhanced Mode
1. **All Standard Features** +
2. **Scene Analysis**: Context understanding
3. **Actor Analysis**: Clothing, pose, objects held
4. **Object Detection**: Comprehensive scene understanding

### 3. Monetization Features
- **Actor Fashion**: Amazon scraping for clothing items
- **Product Discovery**: Reverse image search for scene objects
- **Shopping Integration**: Direct purchase links

### 4. Technical Stack
- **Frontend**: Next.js (cutting-edge version)
- **Backend**: Python with FastAPI
- **Database**: PostgreSQL (Docker)
- **AI Models**: YOLO, Ollama Qwen Vision
- **APIs**: TMDB, Amazon, SerpAPI