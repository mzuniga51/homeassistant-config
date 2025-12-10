# ==============================================================================
# FINAL DEDUPLICATION SCRIPT
# ==============================================================================
# This script will be run from /config/final_dedupe.py
# It uses a manually created library located in /config/my_lib/

# --- Step 1: Manual Library Path Injection ---
# This tells the script to look for our handmade library first.
import sys
sys.path.insert(0, '/config/my_lib')
sys.path.append('/usr/lib/python3.12/site-packages')

# --- Step 2: Standard Imports ---
# Note: We now import 'HomeAssistantClient' from 'homeassistant_ws.client'
import asyncio
from homeassistant_ws.client import HomeAssistantClient


# --- Step 3: Configuration ---
# When running from inside the HA Core container, use localhost
HA_URL = "ws://localhost:8123/api/websocket"
HA_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmMGM2MmNmNTc3MDU0MjM5ODJjNWNjMWRkZWY4YzgwZiIsImlhdCI6MTc2Mzc3NDk0MSwiZXhwIjoyMDc5MTM0OTQxfQ.f6s1XTlNwMitYwei8iQ1HxdA22JIaqT_j3Kdi_ZD6qc"


# --- Step 4: The Main Logic of the Script ---
async def final_interactive_deduplicate():
    """
    Connects to HA and interactively guides the user through deduplicating 
    and cleaning up entities with a '_2' suffix.
    """
    try:
        async with HomeAssistantClient(HA_URL, HA_TOKEN) as client:
            print("✅ Successfully connected to Home Assistant.")

            # Get registry and states for context
            print("Fetching entity registry and states...")
            registry_list = await client.send_command("config/entity_registry/list")
            states_list = await client.send_command("get_states")
            
            entities_by_id = {entity['entity_id']: entity for entity in registry_list}
            states_by_id = {state['entity_id']: state for state in states_list}
            
            # Find potential duplicates (entities ending with '_2')
            potential_duplicates = [
                entity for entity in registry_list if entity['entity_id'].endswith('_2')
            ]

            if not potential_duplicates:
                print("\nNo entities ending in '_2' found. Nothing to do!")
                return

            # Separate into duplicates and orphans
            duplicate_pairs = []
            orphans = []
            
            for entity in potential_duplicates:
                new_entity_id = entity['entity_id']
                original_entity_id = new_entity_id[:-2]
                
                if original_entity_id in entities_by_id:
                    duplicate_pairs.append(entity)
                else:
                    orphans.append(entity)

            print(f"\nFound {len(duplicate_pairs)} duplicate pairs and {len(orphans)} orphans.")
            print("=" * 60)

            # Process duplicate pairs first
            if duplicate_pairs:
                print("\n### PROCESSING DUPLICATE PAIRS ###")
                print("-" * 60)
                
                for new_entity in duplicate_pairs:
                    new_entity_id = new_entity['entity_id']
                    original_entity_id = new_entity_id[:-2]
                    new_status = states_by_id.get(new_entity_id, {}).get('state', 'Not in state machine')
                    original_status = states_by_id.get(original_entity_id, {}).get('state', 'Not in state machine')
                    
                    print(f"Found a potential duplicate pair:")
                    print(f"  - Original: {original_entity_id} (State: {original_status})")
                    print(f"  - New:      {new_entity_id} (State: {new_status})")
                    
                    while True:
                        choice = input("Action: [R]eplace original with new, [S]kip, [Q]uit -> ").lower()
                        if choice in ['r', 's', 'q']: break
                        print("Invalid choice.")

                    if choice == 'q':
                        print("Quitting script.")
                        return
                    if choice == 's':
                        print("Skipping this pair.\n" + "-" * 60)
                        continue
                    
                    if choice == 'r':
                        # Remove old entity
                        try:
                            print(f"  - Removing old entity: {original_entity_id}")
                            await client.send_command("config/entity_registry/remove", {"entity_id": original_entity_id})
                            print(f"  - ✅ Removal successful.")
                        except Exception as e:
                            print(f"  - ⚠️ Could not remove old entity: {e}")
                        
                        # Rename new entity
                        try:
                            print(f"  - Renaming '{new_entity_id}' to '{original_entity_id}'...")
                            await client.send_command("config/entity_registry/update", {"entity_id": new_entity_id, "new_entity_id": original_entity_id})
                            print(f"  - ✅ Rename successful.")
                        except Exception as e:
                            print(f"  - ❌ FAILED to rename: {e}")
                    
                    print("-" * 60)

            # Process orphans second
            if orphans:
                print("\n### PROCESSING ORPHANS ###")
                print("-" * 60)
                
                for new_entity in orphans:
                    new_entity_id = new_entity['entity_id']
                    original_entity_id = new_entity_id[:-2]
                    new_status = states_by_id.get(new_entity_id, {}).get('state', 'Not in state machine')
                    
                    print(f"Found an 'Orphan' entity:")
                    print(f"  - Entity: {new_entity_id} (State: {new_status})")
                    print(f"  - Note: The name '{original_entity_id}' is available.")

                    while True:
                        choice = input("Action: [C]lean up name (remove _2), [S]kip, [Q]uit -> ").lower()
                        if choice in ['c', 's', 'q']: break
                        print("Invalid choice.")

                    if choice == 'q':
                        print("Quitting script.")
                        return
                    if choice == 's':
                        print("Skipping this orphan.\n" + "-" * 60)
                        continue

                    if choice == 'c':
                        # Just rename the orphan, no removal needed
                        try:
                            print(f"  - Renaming '{new_entity_id}' to '{original_entity_id}'...")
                            await client.send_command("config/entity_registry/update", {"entity_id": new_entity_id, "new_entity_id": original_entity_id})
                            print(f"  - ✅ Cleanup successful.")
                        except Exception as e:
                            print(f"  - ❌ FAILED to clean up name: {e}")
                    
                    print("-" * 60)

            print("\n✅ Interactive process finished!")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your HA_URL, HA_TOKEN, and ensure Home Assistant is running.")

# --- Step 5: This makes the script runnable from the command line ---
if __name__ == "__main__":
    asyncio.run(final_interactive_deduplicate())
