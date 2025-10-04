"""
Detailed Vertex AI Connection Error Tracer
Shows exactly where and why the connection fails
"""

import os
import sys
import traceback
from pathlib import Path

print("=" * 70)
print("VERTEX AI CONNECTION ERROR TRACER")
print("=" * 70)

# Step 1: Environment variables
print("\n[STEP 1] Checking environment variables...")
print("-" * 70)

env_vars = {
    'GCP_PROJECT_ID': os.getenv('GCP_PROJECT_ID'),
    'GCP_LOCATION': os.getenv('GCP_LOCATION'),
    'VERTEX_AI_INDEX_ENDPOINT': os.getenv('VERTEX_AI_INDEX_ENDPOINT'),
    'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
}

for key, value in env_vars.items():
    if value:
        if 'CREDENTIALS' in key:
            print(f"✅ {key}: {value}")
            # Check if file exists
            if Path(value).exists():
                print(f"   └─ File exists: YES")
                print(f"   └─ File size: {Path(value).stat().st_size} bytes")
            else:
                print(f"   └─ ❌ File exists: NO")
        else:
            print(f"✅ {key}: {value}")
    else:
        print(f"❌ {key}: NOT SET")

# Step 2: Load from storage.env if not set
print("\n[STEP 2] Loading config/storage.env...")
print("-" * 70)

storage_env = Path("config/storage.env")
if storage_env.exists():
    print(f"✅ Found: {storage_env}")
    try:
        from dotenv import load_dotenv
        load_dotenv(storage_env, override=True)
        print("✅ Loaded environment variables")
        
        # Re-check after loading
        for key in env_vars.keys():
            new_val = os.getenv(key)
            if new_val and new_val != env_vars[key]:
                print(f"   Updated {key}: {new_val}")
                env_vars[key] = new_val
    except ImportError:
        print("⚠️  python-dotenv not installed, skipping")
    except Exception as e:
        print(f"❌ Error loading: {e}")
else:
    print(f"❌ Not found: {storage_env}")

# Step 3: Check google-cloud-aiplatform package
print("\n[STEP 3] Checking google-cloud-aiplatform package...")
print("-" * 70)

try:
    import google.cloud.aiplatform as aiplatform
    print(f"✅ Package installed")
    print(f"   Version: {aiplatform.__version__}")
    VERTEX_AVAILABLE = True
except ImportError as e:
    print(f"❌ Package NOT installed")
    print(f"   Error: {e}")
    print("\n   SOLUTION: Install the package:")
    print("   py -m pip install google-cloud-aiplatform google-auth")
    VERTEX_AVAILABLE = False

if not VERTEX_AVAILABLE:
    print("\n" + "=" * 70)
    print("DIAGNOSIS: Vertex AI package is not installed")
    print("=" * 70)
    print("\nThis is why you see 'Connection failed during initialization'")
    print("The adapter tries to import google.cloud.aiplatform and fails.")
    print("\nRun this command to fix:")
    print("  py -m pip install google-cloud-aiplatform google-auth")
    sys.exit(1)

# Step 4: Test credentials loading
print("\n[STEP 4] Testing credentials loading...")
print("-" * 70)

creds_path = env_vars.get('GOOGLE_APPLICATION_CREDENTIALS')
if not creds_path:
    print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
    sys.exit(1)

# Strip quotes if present
creds_path = creds_path.strip('"').strip("'")
print(f"Credentials path: {creds_path}")

if not Path(creds_path).exists():
    print(f"❌ File does not exist: {creds_path}")
    print("\nSOLUTION: Check the path in config/storage.env")
    sys.exit(1)

try:
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_file(creds_path)
    print(f"✅ Credentials loaded successfully")
    print(f"   Service account: {credentials.service_account_email}")
    print(f"   Project ID: {credentials.project_id}")
except Exception as e:
    print(f"❌ Failed to load credentials: {e}")
    print(f"\nFull error:\n{traceback.format_exc()}")
    sys.exit(1)

# Step 5: Test Vertex AI initialization
print("\n[STEP 5] Testing Vertex AI initialization...")
print("-" * 70)

project_id = env_vars.get('GCP_PROJECT_ID')
location = env_vars.get('GCP_LOCATION', 'us-central1')

if not project_id:
    print("❌ GCP_PROJECT_ID not set")
    sys.exit(1)

print(f"Project ID: {project_id}")
print(f"Location: {location}")

try:
    aiplatform.init(
        project=project_id,
        location=location,
        credentials=credentials
    )
    print("✅ Vertex AI initialized successfully")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    print(f"\nFull error:\n{traceback.format_exc()}")
    print("\nPossible causes:")
    print("  1. Vertex AI API not enabled in GCP project")
    print("  2. Service account lacks permissions")
    print("  3. Invalid project ID")
    print("\nEnable API at:")
    print(f"  https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project={project_id}")
    sys.exit(1)

# Step 6: Test Matching Engine access
print("\n[STEP 6] Testing Matching Engine access...")
print("-" * 70)

try:
    from google.cloud.aiplatform import MatchingEngineIndex
    print("Attempting to list indexes...")
    indexes = MatchingEngineIndex.list()
    print(f"✅ Successfully accessed Matching Engine")
    print(f"   Found {len(indexes)} indexes")
    
    if indexes:
        for idx in indexes:
            print(f"   - {idx.display_name}")
    else:
        print("   (No indexes exist yet - this is normal)")
        
except Exception as e:
    print(f"⚠️  Could not list indexes: {e}")
    print(f"\nFull error:\n{traceback.format_exc()}")
    print("\nThis might be OK if:")
    print("  - This is your first time using Vertex AI")
    print("  - You haven't created any indexes yet")
    print("\nIf you see permission errors, add these roles:")
    print("  - Vertex AI User (roles/aiplatform.user)")
    print("  - Vertex AI Admin (roles/aiplatform.admin)")

# Step 7: Simulate adapter initialization
print("\n[STEP 7] Simulating adapter initialization...")
print("-" * 70)

try:
    # Mimic what the adapter does
    from utils.multi_vector_storage_interface import VectorStoreConfig, VectorStoreType
    
    config = VectorStoreConfig(
        store_type=VectorStoreType.VERTEX_AI_MATCHING,
        connection_params={
            'project_id': project_id,
            'location': location,
            'credentials_path': creds_path,
            'region': location,  # Also try with region
        },
        enabled=True,
        priority=1
    )
    
    print("Creating adapter instance...")
    from utils.adapters.vertex_ai_adapter import VertexAIMatchingEngineAdapter
    
    adapter = VertexAIMatchingEngineAdapter(config)
    print(f"✅ Adapter created")
    print(f"   Project ID: {adapter.project_id}")
    print(f"   Region: {adapter.region}")
    print(f"   Service account path: {adapter.service_account_path}")
    
    print("\nTesting adapter.connect()...")
    import asyncio
    connected = asyncio.run(adapter.connect())
    
    if connected:
        print("✅ Adapter connected successfully!")
    else:
        print("❌ Adapter connection failed")
        
except Exception as e:
    print(f"❌ Adapter initialization failed: {e}")
    print(f"\nFull error:\n{traceback.format_exc()}")

# Summary
print("\n" + "=" * 70)
print("TRACE SUMMARY")
print("=" * 70)

if VERTEX_AVAILABLE:
    print("✅ Package: Installed")
    print(f"✅ Credentials: Valid ({credentials.service_account_email})")
    print(f"✅ Project: {project_id}")
    print(f"✅ Location: {location}")
    print("\nIf adapter still fails in UI:")
    print("  1. Restart Streamlit app")
    print("  2. Click 'Reload Manager' button")
    print("  3. Check logs for detailed error messages")
else:
    print("❌ Package: NOT INSTALLED")
    print("\nInstall command:")
    print("  py -m pip install google-cloud-aiplatform google-auth")

print("=" * 70)
