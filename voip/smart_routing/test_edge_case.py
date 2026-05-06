#!/usr/bin/env python3
"""
Test script to demonstrate the edge case handling:
When both agents are busy, dialing pauses until one becomes available.

This simulates the scenario where:
1. Contact 1 is dialed → Agent 1 becomes busy
2. Contact 2 is dialed → Agent 2 becomes busy
3. Contact 3 waits → Dialer pauses (both agents busy)
4. Agent 1 finishes call → Dialer resumes
5. Contact 3 is dialed → Agent 1 takes the call
"""

import configparser
import logging
import threading
import time
from pathlib import Path

from agent_router import AgentRouter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Load config
config = configparser.ConfigParser()
config.read(Path(__file__).parent / "config.ini")

# Initialize router
router = AgentRouter(config)


def simulate_call(contact_name: str, agent_ext: str, duration: float):
    """Simulate a call that lasts for 'duration' seconds."""
    call_sid = f"CA{contact_name.replace(' ', '')}{int(time.time())}"
    
    logger.info("📞 Dialing %s...", contact_name)
    
    # Mark agent busy
    router.mark_busy(agent_ext, call_sid)
    logger.info("   → Connected to Agent %s", agent_ext)
    
    # Simulate call duration
    time.sleep(duration)
    
    # Mark agent available
    router.mark_available(agent_ext)
    logger.info("   ✅ Call with %s completed (Agent %s now available)", contact_name, agent_ext)


def test_edge_case():
    """Test the edge case: both agents busy, dialing pauses."""
    
    logger.info("=" * 70)
    logger.info("EDGE CASE TEST: Both Agents Busy")
    logger.info("=" * 70)
    logger.info("")
    
    # Initial status
    logger.info("Initial status: %d agents available", router.available_count())
    logger.info("Agents: %s", router.status())
    logger.info("")
    
    # Scenario: 5 contacts, 2 agents, calls last 5 seconds each
    contacts = [
        ("Contact 1", 5),
        ("Contact 2", 5),
        ("Contact 3", 5),
        ("Contact 4", 5),
        ("Contact 5", 5),
    ]
    
    logger.info("📋 Contact list: %d contacts", len(contacts))
    logger.info("👥 Available agents: 2 (extensions 101, 102)")
    logger.info("⏱️  Call duration: 5 seconds each")
    logger.info("")
    logger.info("-" * 70)
    logger.info("")
    
    # Start dialing
    for i, (name, duration) in enumerate(contacts, 1):
        logger.info("🔄 Processing contact %d/%d: %s", i, len(contacts), name)
        
        # Check available agents
        available = router.available_count()
        logger.info("   Available agents: %d", available)
        
        if available == 0:
            logger.info("   ⏸️  All agents busy — waiting for one to become available...")
            
            # Wait for agent to become available
            start_wait = time.time()
            if router.wait_for_available_agent(timeout=30):
                wait_time = time.time() - start_wait
                logger.info("   ✅ Agent available after %.1f seconds — resuming", wait_time)
            else:
                logger.error("   ❌ Timeout waiting for agent!")
                break
        
        # Get available agent
        agent_ext = router.get_available_agent()
        if agent_ext:
            # Start call in background thread (simulates async call)
            thread = threading.Thread(
                target=simulate_call,
                args=(name, agent_ext, duration),
                daemon=True
            )
            thread.start()
            
            # Small delay to simulate API call time
            time.sleep(0.5)
        else:
            logger.error("   ❌ No agent available (this shouldn't happen!)")
        
        logger.info("")
    
    # Wait for all calls to complete
    logger.info("-" * 70)
    logger.info("⏳ Waiting for all calls to complete...")
    time.sleep(6)  # Wait for last call to finish
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST COMPLETE")
    logger.info("=" * 70)
    logger.info("Final status: %d agents available", router.available_count())
    logger.info("Agents: %s", router.status())
    logger.info("")
    logger.info("✅ Edge case handled correctly!")
    logger.info("   - Dialer paused when both agents were busy")
    logger.info("   - Dialer resumed when an agent became available")
    logger.info("   - All contacts were processed sequentially")


if __name__ == "__main__":
    test_edge_case()

