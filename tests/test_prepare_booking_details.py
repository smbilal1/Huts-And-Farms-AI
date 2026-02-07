"""
Test script for prepare_booking_details tool.

This script tests the new booking details collection workflow.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.agents.tools.booking_details_tools import prepare_booking_details
from app.models.user import User, Session
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
import uuid


def test_new_user_flow():
    """Test flow for new user without name/CNIC"""
    print("\n" + "="*80)
    print("TEST 1: New User (No Name/CNIC)")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test user without name/CNIC
        user_repo = UserRepository()
        session_repo = SessionRepository()
        
        test_phone = f"+92300{uuid.uuid4().hex[:7]}"
        user = user_repo.create(db, {
            "phone_number": test_phone,
            "name": None,
            "cnic": None
        })
        
        # Create session
        session = session_repo.create(db, {
            "id": f"test_session_{uuid.uuid4().hex[:8]}",
            "user_id": user.user_id,
            "source": "Bot"
        })
        
        print(f"✅ Created test user: {user.user_id}")
        print(f"✅ Created test session: {session.id}")
        
        # Step 1: Check what's needed
        print("\n--- Step 1: Initial check ---")
        result = prepare_booking_details.invoke({"session_id": session.id})
        print(f"Result: {result}")
        
        assert result["ready"] == False, "Should not be ready"
        assert "user_name" in result["questions_needed"], "Should need user_name"
        assert "cnic" in result["questions_needed"], "Should need cnic"
        print("✅ Correctly identified missing fields")
        
        # Step 2: User provides details
        print("\n--- Step 2: User provides details ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "user_name": "Ahmed Ali",
            "cnic": "1234567890123"
        })
        print(f"Result: {result}")
        
        assert result["ready"] == True, "Should be ready now"
        assert result["confirmed"] == True, "Should be confirmed"
        print("✅ Details saved and confirmed")
        
        # Verify in database
        db.refresh(user)
        assert user.name == "Ahmed Ali", "Name should be saved"
        assert user.cnic == "1234567890123", "CNIC should be saved"
        print("✅ Details verified in database")
        
        # Cleanup
        db.delete(session)
        db.delete(user)
        db.commit()
        print("✅ Test cleanup completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_existing_user_flow():
    """Test flow for existing user with name/CNIC"""
    print("\n" + "="*80)
    print("TEST 2: Existing User (Has Name/CNIC)")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test user WITH name/CNIC
        user_repo = UserRepository()
        session_repo = SessionRepository()
        
        test_phone = f"+92300{uuid.uuid4().hex[:7]}"
        user = user_repo.create(db, {
            "phone_number": test_phone,
            "name": "Ahmed Ali",
            "cnic": "1234567890123"
        })
        
        # Create session
        session = session_repo.create(db, {
            "id": f"test_session_{uuid.uuid4().hex[:8]}",
            "user_id": user.user_id,
            "source": "Bot"
        })
        
        print(f"✅ Created test user with details: {user.user_id}")
        print(f"✅ Created test session: {session.id}")
        
        # Step 1: Check - should ask for confirmation
        print("\n--- Step 1: Initial check ---")
        result = prepare_booking_details.invoke({"session_id": session.id})
        print(f"Result: {result}")
        
        assert result["ready"] == False, "Should not be ready yet"
        assert result["needs_confirmation"] == True, "Should need confirmation"
        assert result["current_name"] == "Ahmed Ali", "Should show current name"
        assert result["current_cnic"] == "1234567890123", "Should show current CNIC"
        print("✅ Correctly asked for confirmation")
        
        # Step 2: User confirms
        print("\n--- Step 2: User confirms ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "action": "Confirm and Book"
        })
        print(f"Result: {result}")
        
        assert result["ready"] == True, "Should be ready now"
        assert result["confirmed"] == True, "Should be confirmed"
        print("✅ Confirmation successful")
        
        # Cleanup
        db.delete(session)
        db.delete(user)
        db.commit()
        print("✅ Test cleanup completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_edit_details_flow():
    """Test flow for editing existing details"""
    print("\n" + "="*80)
    print("TEST 3: Edit Existing Details")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test user WITH name/CNIC
        user_repo = UserRepository()
        session_repo = SessionRepository()
        
        test_phone = f"+92300{uuid.uuid4().hex[:7]}"
        user = user_repo.create(db, {
            "phone_number": test_phone,
            "name": "Ahmed Ali",
            "cnic": "1234567890123"
        })
        
        # Create session
        session = session_repo.create(db, {
            "id": f"test_session_{uuid.uuid4().hex[:8]}",
            "user_id": user.user_id,
            "source": "Bot"
        })
        
        print(f"✅ Created test user: {user.user_id}")
        
        # Step 1: User wants to edit
        print("\n--- Step 1: User selects Edit Details ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "action": "Edit Details"
        })
        print(f"Result: {result}")
        
        assert result["ready"] == False, "Should not be ready"
        assert result["editing"] == True, "Should be in editing mode"
        print("✅ Edit mode activated")
        
        # Step 2: User updates CNIC
        print("\n--- Step 2: User updates CNIC ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "user_name": "Ahmed Ali",  # Keep same
            "cnic": "9876543210123"     # Change CNIC
        })
        print(f"Result: {result}")
        
        assert result["ready"] == True, "Should be ready"
        assert result["confirmed"] == True, "Should be confirmed"
        print("✅ Details updated")
        
        # Verify in database
        db.refresh(user)
        assert user.name == "Ahmed Ali", "Name should remain same"
        assert user.cnic == "9876543210123", "CNIC should be updated"
        print("✅ Changes verified in database")
        
        # Cleanup
        db.delete(session)
        db.delete(user)
        db.commit()
        print("✅ Test cleanup completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_cnic_validation():
    """Test CNIC validation"""
    print("\n" + "="*80)
    print("TEST 4: CNIC Validation")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Create test user
        user_repo = UserRepository()
        session_repo = SessionRepository()
        
        test_phone = f"+92300{uuid.uuid4().hex[:7]}"
        user = user_repo.create(db, {
            "phone_number": test_phone,
            "name": None,
            "cnic": None
        })
        
        session = session_repo.create(db, {
            "id": f"test_session_{uuid.uuid4().hex[:8]}",
            "user_id": user.user_id,
            "source": "Bot"
        })
        
        print(f"✅ Created test user: {user.user_id}")
        
        # Test invalid CNIC (too short)
        print("\n--- Test: Invalid CNIC (too short) ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "user_name": "Ahmed Ali",
            "cnic": "12345"  # Only 5 digits
        })
        print(f"Result: {result}")
        
        assert result["ready"] == False, "Should not be ready"
        assert "validation_errors" in result, "Should have validation errors"
        assert any("13 digits" in str(err) for err in result["validation_errors"]), "Should mention 13 digits"
        print("✅ Correctly rejected short CNIC")
        
        # Test invalid CNIC (too long)
        print("\n--- Test: Invalid CNIC (too long) ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "user_name": "Ahmed Ali",
            "cnic": "12345678901234"  # 14 digits
        })
        print(f"Result: {result}")
        
        assert result["ready"] == False, "Should not be ready"
        assert "validation_errors" in result, "Should have validation errors"
        print("✅ Correctly rejected long CNIC")
        
        # Test valid CNIC
        print("\n--- Test: Valid CNIC ---")
        result = prepare_booking_details.invoke({
            "session_id": session.id,
            "user_name": "Ahmed Ali",
            "cnic": "1234567890123"  # Exactly 13 digits
        })
        print(f"Result: {result}")
        
        assert result["ready"] == True, "Should be ready"
        assert result["confirmed"] == True, "Should be confirmed"
        print("✅ Correctly accepted valid CNIC")
        
        # Cleanup
        db.delete(session)
        db.delete(user)
        db.commit()
        print("✅ Test cleanup completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PREPARE_BOOKING_DETAILS TOOL")
    print("="*80)
    
    try:
        test_new_user_flow()
        test_existing_user_flow()
        test_edit_details_flow()
        test_cnic_validation()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80 + "\n")
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ TESTS FAILED: {e}")
        print("="*80 + "\n")
        raise
