"""
Tests for Phase 1 — Profile Foundation.

Tests:
  - Completeness calculation with full profile (~78)
  - Completeness calculation with empty profile (0)
  - PATCH updates specific fields correctly (deep merge)
  - JSON storage atomic write creates file correctly
"""

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from backend.services.profile_service import calculate_completeness
from backend.storage.json_store import write_json_atomic


# --- Fixtures ---

@pytest.fixture
def full_profile():
    """Load the actual profile.json for testing."""
    profile_path = Path(__file__).resolve().parent.parent / "data" / "profile.json"
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def empty_profile():
    """Return a minimal empty profile."""
    return {}


@pytest.fixture
def partial_profile():
    """Return a profile with only personal_info filled."""
    return {
        "personal_info": {
            "full_name": "Test User",
            "headline": "Developer",
            "contact": {
                "email": "test@example.com"
            },
            "location": {
                "city": "TestCity"
            }
        }
    }


# --- Completeness Scoring Tests ---

class TestCompletenessCalculation:
    """Tests for calculate_completeness function."""

    def test_full_profile_score(self, full_profile):
        """
        Test completeness with actual profile.json.
        
        The current profile has email, phone, linkedin, github, portfolio 
        filled but is missing exact_education_dates (education[0].start_date 
        is null) and gpa (education[0].grade is null).
        Expected score: ~78 based on PRD meta.completeness_score.
        """
        result = calculate_completeness(full_profile)

        assert "score" in result
        assert "missing_fields" in result
        assert isinstance(result["score"], (int, float))
        assert isinstance(result["missing_fields"], list)

        # PRD says completeness_score is 78 for current data
        # Allow ±4 tolerance for weight rounding
        assert 74 <= result["score"] <= 82, (
            f"Expected score ~78, got {result['score']}. "
            f"Missing: {result['missing_fields']}"
        )

        # These should be in missing fields based on PRD
        assert "exact_education_dates" in result["missing_fields"]
        assert "gpa" in result["missing_fields"]

    def test_empty_profile_score(self, empty_profile):
        """
        Test completeness with empty profile returns 0 and all fields missing.
        """
        result = calculate_completeness(empty_profile)

        assert result["score"] == 0
        assert len(result["missing_fields"]) > 0

    def test_none_profile_score(self):
        """Test completeness with None returns 0."""
        result = calculate_completeness(None)
        assert result["score"] == 0

    def test_partial_profile_score(self, partial_profile):
        """
        Test completeness with partial profile returns intermediate score.
        Only personal_info.full_name, headline, email, and city are filled.
        """
        result = calculate_completeness(partial_profile)

        assert 0 < result["score"] < 100
        assert "full_name" not in result["missing_fields"]
        assert "headline" not in result["missing_fields"]
        assert "email" not in result["missing_fields"]
        assert "location_city" not in result["missing_fields"]

        # These should be missing
        assert "work_experience" in result["missing_fields"]
        assert "education" in result["missing_fields"]
        assert "skills" in result["missing_fields"]
        assert "projects" in result["missing_fields"]


# --- PATCH / Deep Merge Tests ---

class TestPatchProfile:
    """Tests for profile update (deep merge) logic."""

    def test_patch_updates_nested_field(self, full_profile):
        """Test that deep merge correctly updates a nested field."""
        from backend.routers.profile import _deep_merge

        updates = {
            "personal_info": {
                "contact": {
                    "phone": "+1999999999"
                }
            }
        }

        merged = _deep_merge(full_profile, updates)

        # Updated field should have new value
        assert merged["personal_info"]["contact"]["phone"] == "+1999999999"

        # Other nested fields should be preserved
        assert merged["personal_info"]["contact"]["email"] == full_profile["personal_info"]["contact"]["email"]
        assert merged["personal_info"]["full_name"] == full_profile["personal_info"]["full_name"]

    def test_patch_preserves_unrelated_sections(self, full_profile):
        """Test that patching one section doesn't affect others."""
        from backend.routers.profile import _deep_merge

        updates = {"personal_info": {"headline": "New Headline"}}
        merged = _deep_merge(full_profile, updates)

        # Updated field
        assert merged["personal_info"]["headline"] == "New Headline"

        # Unrelated sections unchanged
        assert merged["education"] == full_profile["education"]
        assert merged["skills"] == full_profile["skills"]
        assert merged["projects"] == full_profile["projects"]

    def test_patch_adds_new_field(self, full_profile):
        """Test that deep merge can add entirely new fields."""
        from backend.routers.profile import _deep_merge

        updates = {"new_section": {"key": "value"}}
        merged = _deep_merge(full_profile, updates)

        assert merged["new_section"]["key"] == "value"
        # Original data preserved
        assert merged["personal_info"] == full_profile["personal_info"]


# --- Atomic Write Tests ---

class TestAtomicWrite:
    """Tests for JSON storage atomic write."""

    def test_atomic_write_creates_file(self):
        """Test that write_json_atomic creates the file with correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test_output.json"
            data = {"test": "value", "number": 42}

            write_json_atomic(target, data)

            assert target.exists()
            with open(target, "r", encoding="utf-8") as f:
                written = json.load(f)
            assert written == data

    def test_atomic_write_no_temp_file_left(self):
        """Test that no .tmp file remains after successful write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test_clean.json"
            data = {"clean": True}

            write_json_atomic(target, data)

            tmp_file = target.with_suffix(".tmp")
            assert not tmp_file.exists()

    def test_atomic_write_overwrites_existing(self):
        """Test that atomic write replaces existing file content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "test_overwrite.json"

            # Write initial
            write_json_atomic(target, {"version": 1})
            # Overwrite
            write_json_atomic(target, {"version": 2})

            with open(target, "r", encoding="utf-8") as f:
                result = json.load(f)
            assert result["version"] == 2

    def test_atomic_write_creates_parent_dirs(self):
        """Test that atomic write creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "sub" / "dir" / "deep.json"
            data = {"nested": True}

            write_json_atomic(target, data)

            assert target.exists()
            with open(target, "r", encoding="utf-8") as f:
                written = json.load(f)
            assert written == data
