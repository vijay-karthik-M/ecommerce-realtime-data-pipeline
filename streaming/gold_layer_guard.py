"""
GOLD LAYER WRITE GATE
====================

Prevents writes to Gold layer until data quality requirements are met.
Implements blocking logic for failed quality checks.
"""

import json
import os
from datetime import datetime
from pathlib import Path


class GoldLayerGuard:
    """Gate keeper for Gold layer write operations"""
    
    def __init__(self, reports_dir="data_quality/reports"):
        self.reports_dir = reports_dir
        self.latest_report = None
        self.quality_gates = {
            "schema_validation": {"critical": True, "description": "Column types and structure"},
            "null_checks": {"critical": True, "description": "No nulls in required columns"},
            "range_constraints": {"critical": False, "description": "Values within valid ranges"},
            "set_membership": {"critical": True, "description": "Valid enum values"},
            "uniqueness_checks": {"critical": False, "description": "Expected duplication patterns"},
            "referential_integrity": {"critical": True, "description": "Data consistency"},
            "completeness_freshness": {"critical": True, "description": "Data quality and recency"}
        }
    
    def load_latest_report(self):
        """Load the most recent quality report"""
        report_files = sorted(Path(self.reports_dir).glob("data_quality_report_*.json"))
        if not report_files:
            return None
        
        with open(report_files[-1], 'r') as f:
            self.latest_report = json.load(f)
        
        return self.latest_report
    
    def can_write_to_gold(self, fail_hard=False):
        """
        Check if Gold layer writes are approved
        
        Args:
            fail_hard: If True, raise exception on failures. If False, return boolean.
        
        Returns:
            bool: True if all quality gates pass, False otherwise
        """
        
        report = self.load_latest_report()
        if report is None:
            msg = "❌ No quality report found. Run validation first."
            if fail_hard:
                raise Exception(msg)
            print(msg)
            return False
        
        print("\n" + "="*80)
        print("🔐 GOLD LAYER WRITE AUTHORIZATION CHECK")
        print("="*80)
        print(f"Report Timestamp: {report['timestamp']}\n")
        
        critical_failures = []
        non_critical_failures = []
        
        for suite in report["suites"]:
            suite_name = suite["suite_name"]
            gate_config = self.quality_gates.get(suite_name, {})
            is_critical = gate_config.get("critical", False)
            description = gate_config.get("description", "")
            
            if suite["failed"] > 0:
                status_msg = f"❌ {suite_name}: {suite['failed']} failures"
                if is_critical:
                    critical_failures.append({
                        "suite": suite_name,
                        "description": description,
                        "failures": suite["failed"]
                    })
                    print(f"{status_msg} [CRITICAL - BLOCKS WRITES]")
                else:
                    non_critical_failures.append({
                        "suite": suite_name,
                        "description": description,
                        "failures": suite["failed"]
                    })
                    print(f"{status_msg} [WARNING - Non-critical]")
            else:
                print(f"✅ {suite_name}: All expectations passed")
        
        print("\n" + "="*80)
        
        # Determine write eligibility
        write_approved = len(critical_failures) == 0
        
        if write_approved:
            print("✅ ALL CRITICAL QUALITY GATES PASSED")
            print("   Gold layer writes are APPROVED")
            
            if non_critical_failures:
                print("\n⚠️  Non-critical failures detected (advisory):")
                for failure in non_critical_failures:
                    print(f"   • {failure['suite']}: {failure['failures']} issues")
                print("   Review these before production deployment.")
        else:
            print("❌ CRITICAL QUALITY GATE FAILURES DETECTED")
            print("   Gold layer writes are BLOCKED")
            print("\n   Critical failures:")
            for failure in critical_failures:
                print(f"   • {failure['suite']}: {failure['failures']} issues")
                print(f"     {failure['description']}")
            print("\n   Action Required: Fix critical quality issues and re-run validation")
        
        print("="*80 + "\n")
        
        if fail_hard and not write_approved:
            raise Exception(f"Gold layer write blocked: {len(critical_failures)} critical quality gate(s) failed")
        
        return write_approved
    
    def generate_quality_summary(self):
        """Generate human-readable quality summary"""
        report = self.load_latest_report()
        if report is None:
            return "No quality report available"
        
        summary = report["summary"]
        
        output = f"""
DATA QUALITY SUMMARY REPORT
===========================
Generated: {report['timestamp']}

Overall Metrics:
  • Total Expectations: {summary['total_expectations']}
  • Passed: {summary['total_passed']}
  • Failed: {summary['total_failed']}
  • Pass Rate: {(summary['total_passed']/summary['total_expectations']*100):.1f}%

Suites Status:
  • Passed: {summary['suites_passed']}/7
  • Failed: {summary['suites_failed']}/7

Quality Gate Status:
"""
        
        for suite in report["suites"]:
            gate_config = self.quality_gates.get(suite["suite_name"], {})
            is_critical = "[CRITICAL]" if gate_config.get("critical") else "[ADVISORY]"
            status = "✅ PASS" if suite["failed"] == 0 else f"❌ FAIL ({suite['failed']} issues)"
            output += f"  • {suite['suite_name']}: {status} {is_critical}\n"
        
        return output


def check_gold_layer_approval(reports_dir="data_quality/reports"):
    """
    Utility function to check if Gold layer is approved for writes
    
    Usage:
        from streaming.gold_layer_guard import check_gold_layer_approval
        
        if check_gold_layer_approval():
            # Proceed with Gold layer processing
            pass
    """
    guard = GoldLayerGuard(reports_dir)
    return guard.can_write_to_gold(fail_hard=False)


if __name__ == "__main__":
    guard = GoldLayerGuard()
    
    print(guard.generate_quality_summary())
    
    approved = guard.can_write_to_gold()
    
    exit(0 if approved else 1)
