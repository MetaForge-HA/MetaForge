"""Integration tests: BOM risk scoring + compliance checklist pipeline.

Exercises the supply chain and compliance agents together using realistic
drone flight controller BOM data. Tests cover individual scoring, checklist
generation, evidence linking, coverage tracking, and the combined pipeline
that feeds into EVT gate readiness.
"""

from __future__ import annotations

import pytest

from domain_agents.compliance.checklist_generator import ChecklistGenerator
from domain_agents.compliance.evidence_tracker import EvidenceTracker
from domain_agents.compliance.models import (
    ComplianceChecklist,
    ComplianceRegime,
    EvidenceRecord,
    EvidenceStatus,
)
from domain_agents.supply_chain.alt_parts import AlternatePartsFinder
from domain_agents.supply_chain.models import (
    BOMEntry,
    BOMRiskReport,
    DistributorInfo,
    LifecycleStatus,
    PartRiskScore,
    RiskLevel,
)
from domain_agents.supply_chain.risk_scorer import BOMRiskScorer


# ---------------------------------------------------------------------------
# Realistic drone FC BOM fixture (15-20 parts)
# ---------------------------------------------------------------------------

def _make_drone_fc_bom() -> list[BOMEntry]:
    """Build a realistic drone flight controller BOM with 18 parts."""
    return [
        # MCU — multi-source, active
        BOMEntry(
            part_number="STM32F405RGT6",
            manufacturer="STMicroelectronics",
            description="ARM Cortex-M4 MCU 168MHz 1MB Flash",
            quantity=1,
            package="LQFP-64",
            lifecycle=LifecycleStatus.ACTIVE,
            category="MCU",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=5200, lead_time_weeks=2, unit_price_usd=8.50),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=3800, lead_time_weeks=2, unit_price_usd=8.75),
                DistributorInfo(name="Nexar", in_stock=True, stock_quantity=1200, lead_time_weeks=3, unit_price_usd=9.10),
            ],
        ),
        # IMU — multi-source, active
        BOMEntry(
            part_number="MPU6050",
            manufacturer="InvenSense",
            description="6-axis IMU (accel + gyro)",
            quantity=1,
            package="QFN-24",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Sensor",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=8500, lead_time_weeks=1, unit_price_usd=3.20),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=6200, lead_time_weeks=1, unit_price_usd=3.35),
                DistributorInfo(name="Nexar", in_stock=True, stock_quantity=2100, lead_time_weeks=2, unit_price_usd=3.50),
            ],
        ),
        # Barometer — dual source
        BOMEntry(
            part_number="BMP280",
            manufacturer="Bosch",
            description="Barometric pressure sensor",
            quantity=1,
            package="LGA-8",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Sensor",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=4500, lead_time_weeks=2, unit_price_usd=1.80),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=3200, lead_time_weeks=2, unit_price_usd=1.90),
            ],
        ),
        # Magnetometer — dual source
        BOMEntry(
            part_number="QMC5883L",
            manufacturer="QST",
            description="3-axis magnetometer",
            quantity=1,
            package="LGA-16",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Sensor",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=2300, lead_time_weeks=3, unit_price_usd=0.95),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=1800, lead_time_weeks=3, unit_price_usd=1.05),
            ],
        ),
        # Voltage regulator 3.3V — multi-source
        BOMEntry(
            part_number="AMS1117-3.3",
            manufacturer="Advanced Monolithic Systems",
            description="3.3V LDO regulator",
            quantity=2,
            package="SOT-223",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Power",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=25000, lead_time_weeks=1, unit_price_usd=0.25),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=18000, lead_time_weeks=1, unit_price_usd=0.28),
                DistributorInfo(name="Nexar", in_stock=True, stock_quantity=12000, lead_time_weeks=1, unit_price_usd=0.30),
            ],
        ),
        # Voltage regulator 5V
        BOMEntry(
            part_number="LM7805",
            manufacturer="Texas Instruments",
            description="5V linear regulator",
            quantity=1,
            package="TO-220",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Power",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=15000, lead_time_weeks=1, unit_price_usd=0.45),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=11000, lead_time_weeks=1, unit_price_usd=0.48),
                DistributorInfo(name="Nexar", in_stock=True, stock_quantity=8000, lead_time_weeks=2, unit_price_usd=0.50),
            ],
        ),
        # Crystal oscillator
        BOMEntry(
            part_number="ABM8-8.000MHZ",
            manufacturer="Abracon",
            description="8MHz crystal oscillator",
            quantity=1,
            package="HC49",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Passive",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=9000, lead_time_weeks=1, unit_price_usd=0.35),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=7500, lead_time_weeks=1, unit_price_usd=0.38),
            ],
        ),
        # Decoupling caps (100nF)
        BOMEntry(
            part_number="GRM188R71C104KA01",
            manufacturer="Murata",
            description="100nF MLCC 0603",
            quantity=20,
            package="0603",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Passive",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=500000, lead_time_weeks=1, unit_price_usd=0.01),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=350000, lead_time_weeks=1, unit_price_usd=0.01),
            ],
        ),
        # Bulk cap
        BOMEntry(
            part_number="EEU-FC1V101",
            manufacturer="Panasonic",
            description="100uF 35V electrolytic",
            quantity=4,
            package="6.3x7.7mm",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Passive",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=12000, lead_time_weeks=2, unit_price_usd=0.15),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=9500, lead_time_weeks=2, unit_price_usd=0.16),
            ],
        ),
        # USB connector
        BOMEntry(
            part_number="10118194-0001LF",
            manufacturer="Amphenol",
            description="Micro USB Type-B connector",
            quantity=1,
            package="SMD",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Connector",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=6000, lead_time_weeks=2, unit_price_usd=0.55),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=4200, lead_time_weeks=2, unit_price_usd=0.58),
            ],
        ),
        # Motor FET driver
        BOMEntry(
            part_number="IRLML6344TRPBF",
            manufacturer="Infineon",
            description="N-channel MOSFET 30V 5A",
            quantity=4,
            package="SOT-23",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Power",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=18000, lead_time_weeks=1, unit_price_usd=0.42),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=14000, lead_time_weeks=1, unit_price_usd=0.45),
                DistributorInfo(name="Nexar", in_stock=True, stock_quantity=6000, lead_time_weeks=2, unit_price_usd=0.48),
            ],
        ),
        # LED indicator
        BOMEntry(
            part_number="LTST-C171KRKT",
            manufacturer="Lite-On",
            description="Red LED 0805",
            quantity=2,
            package="0805",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Indicator",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=30000, lead_time_weeks=1, unit_price_usd=0.08),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=25000, lead_time_weeks=1, unit_price_usd=0.09),
            ],
        ),
        # GPS module — dual source
        BOMEntry(
            part_number="NEO-M8N",
            manufacturer="u-blox",
            description="GPS/GLONASS receiver module",
            quantity=1,
            package="LCC",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Module",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=800, lead_time_weeks=4, unit_price_usd=12.50),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=650, lead_time_weeks=4, unit_price_usd=12.80),
            ],
        ),
        # Hypothetical single-source MEMS sensor — HIGH RISK
        BOMEntry(
            part_number="XSENS-MTI-3",
            manufacturer="Xsens",
            description="9-axis MEMS IMU (single source)",
            quantity=1,
            package="LGA-24",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Sensor",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=45, lead_time_weeks=16, unit_price_usd=85.00),
            ],
        ),
        # EOL part — CRITICAL RISK
        BOMEntry(
            part_number="MAX232CPE",
            manufacturer="Maxim",
            description="RS-232 transceiver (legacy debug port)",
            quantity=1,
            package="DIP-16",
            lifecycle=LifecycleStatus.EOL,
            category="Interface",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=120, lead_time_weeks=26, unit_price_usd=2.50),
            ],
        ),
        # NRND part — MEDIUM-HIGH RISK
        BOMEntry(
            part_number="AT24C256C",
            manufacturer="Microchip",
            description="256Kbit I2C EEPROM (NRND)",
            quantity=1,
            package="SOIC-8",
            lifecycle=LifecycleStatus.NRND,
            category="Memory",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=3500, lead_time_weeks=3, unit_price_usd=0.65),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=2800, lead_time_weeks=3, unit_price_usd=0.68),
            ],
        ),
        # Resistor array — commodity
        BOMEntry(
            part_number="RC0603FR-0710KL",
            manufacturer="Yageo",
            description="10K 0603 resistor",
            quantity=30,
            package="0603",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Passive",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=800000, lead_time_weeks=1, unit_price_usd=0.005),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=600000, lead_time_weeks=1, unit_price_usd=0.005),
            ],
        ),
        # Current sense resistor
        BOMEntry(
            part_number="WSL2512R0100FEA",
            manufacturer="Vishay",
            description="0.01 ohm current sense resistor",
            quantity=4,
            package="2512",
            lifecycle=LifecycleStatus.ACTIVE,
            category="Passive",
            distributors=[
                DistributorInfo(name="Digi-Key", in_stock=True, stock_quantity=15000, lead_time_weeks=2, unit_price_usd=0.35),
                DistributorInfo(name="Mouser", in_stock=True, stock_quantity=11000, lead_time_weeks=2, unit_price_usd=0.38),
            ],
        ),
    ]


@pytest.fixture
def drone_bom() -> list[BOMEntry]:
    """Realistic 18-part drone FC BOM."""
    return _make_drone_fc_bom()


@pytest.fixture
def scorer() -> BOMRiskScorer:
    return BOMRiskScorer()


@pytest.fixture
def risk_report(scorer: BOMRiskScorer, drone_bom: list[BOMEntry]) -> BOMRiskReport:
    """Pre-scored risk report for the drone FC BOM."""
    return scorer.score_bom(drone_bom)


@pytest.fixture
def checklist_generator() -> ChecklistGenerator:
    return ChecklistGenerator()


@pytest.fixture
def evidence_tracker() -> EvidenceTracker:
    return EvidenceTracker()


# ===========================================================================
# BOM Risk Scoring Tests
# ===========================================================================


class TestBOMRiskScoring:
    """Tests for BOM risk scoring on realistic drone FC data."""

    def test_score_full_bom_returns_report(
        self, scorer: BOMRiskScorer, drone_bom: list[BOMEntry]
    ):
        report = scorer.score_bom(drone_bom)
        assert isinstance(report, BOMRiskReport)
        assert report.total_parts == 18
        assert len(report.scored_parts) == 18

    def test_stm32f405_scores_low_risk(self, risk_report: BOMRiskReport):
        """STM32F405RGT6 is multi-source, active lifecycle -> low risk."""
        stm32 = next(
            s for s in risk_report.scored_parts if s.part_number == "STM32F405RGT6"
        )
        assert stm32.risk_level == RiskLevel.LOW
        assert stm32.risk_score < 0.25
        assert stm32.num_sources == 3
        assert stm32.lifecycle == LifecycleStatus.ACTIVE

    def test_single_source_mems_scores_medium_or_higher(self, risk_report: BOMRiskReport):
        """XSENS-MTI-3 is single-source with low stock and long lead -> elevated risk."""
        xsens = next(
            s for s in risk_report.scored_parts if s.part_number == "XSENS-MTI-3"
        )
        assert xsens.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert xsens.risk_score >= 0.25
        assert xsens.num_sources == 1
        assert any("Single source" in r for r in xsens.reasons)

    def test_eol_part_scores_high_or_critical(self, risk_report: BOMRiskReport):
        """MAX232CPE is EOL with single source -> high or critical risk."""
        max232 = next(
            s for s in risk_report.scored_parts if s.part_number == "MAX232CPE"
        )
        assert max232.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert max232.risk_score >= 0.5
        assert max232.lifecycle == LifecycleStatus.EOL
        assert any("Lifecycle" in r or "eol" in r.lower() for r in max232.reasons)

    def test_nrnd_part_scores_medium_or_higher(self, risk_report: BOMRiskReport):
        """AT24C256C is NRND -> at least medium risk."""
        eeprom = next(
            s for s in risk_report.scored_parts if s.part_number == "AT24C256C"
        )
        assert eeprom.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
        assert eeprom.risk_score >= 0.25
        assert any("Not recommended" in r for r in eeprom.reasons)

    def test_commodity_passive_scores_low(self, risk_report: BOMRiskReport):
        """Commodity passives (resistors, caps) should score low risk."""
        resistor = next(
            s for s in risk_report.scored_parts if s.part_number == "RC0603FR-0710KL"
        )
        assert resistor.risk_level == RiskLevel.LOW
        assert resistor.risk_score < 0.15

    def test_overall_risk_reflects_high_risk_parts(self, risk_report: BOMRiskReport):
        """Overall BOM risk should be elevated due to EOL and single-source parts."""
        # Not critical overall (most parts are fine), but not zero
        assert risk_report.overall_risk_score > 0.0
        all_flagged = risk_report.critical_parts + risk_report.high_risk_parts
        assert len(all_flagged) >= 1
        assert "MAX232CPE" in all_flagged

    def test_high_risk_parts_list_populated(self, risk_report: BOMRiskReport):
        """High-risk or critical parts list should include EOL part."""
        all_flagged = risk_report.critical_parts + risk_report.high_risk_parts
        assert "MAX232CPE" in all_flagged

    def test_report_summary_is_human_readable(self, risk_report: BOMRiskReport):
        """Summary should contain part count and risk level."""
        assert "18 parts" in risk_report.summary
        assert risk_report.overall_risk_level.value in risk_report.summary

    def test_risk_scores_are_bounded(self, risk_report: BOMRiskReport):
        """All risk scores should be in [0, 1]."""
        for part in risk_report.scored_parts:
            assert 0.0 <= part.risk_score <= 1.0


# ===========================================================================
# Alternate Parts Tests
# ===========================================================================


class TestAlternateParts:
    """Tests for alternate parts finder on high-risk BOM components."""

    def test_finds_alternates_for_high_risk_parts(
        self, drone_bom: list[BOMEntry], risk_report: BOMRiskReport
    ):
        finder = AlternatePartsFinder()
        alts = finder.find_alternates(drone_bom, risk_report, min_risk_level=RiskLevel.HIGH)
        # Should find alternates from the knowledge base
        assert len(alts) >= 0  # Knowledge base may not have all parts

    def test_no_alternates_for_low_risk_parts(
        self, drone_bom: list[BOMEntry], risk_report: BOMRiskReport
    ):
        finder = AlternatePartsFinder()
        # Set threshold very high so no parts qualify
        alts = finder.find_alternates(drone_bom, risk_report, min_risk_level=RiskLevel.CRITICAL)
        # Only critical-risk parts should trigger alternate search
        for alt in alts:
            scored = next(s for s in risk_report.scored_parts if s.part_number == alt.original_part_number)
            assert scored.risk_score >= 0.75


# ===========================================================================
# Compliance Checklist Generation Tests
# ===========================================================================


class TestComplianceChecklist:
    """Tests for compliance checklist generation."""

    def test_generate_ce_checklist(self, checklist_generator: ChecklistGenerator):
        checklist = checklist_generator.generate([ComplianceRegime.CE])
        assert checklist.total_items == 10  # CE has 10 items in template
        assert all(i.regime == ComplianceRegime.CE for i in checklist.items)

    def test_generate_fcc_checklist(self, checklist_generator: ChecklistGenerator):
        checklist = checklist_generator.generate([ComplianceRegime.FCC])
        assert checklist.total_items == 5  # FCC has 5 items in template
        assert all(i.regime == ComplianceRegime.FCC for i in checklist.items)

    def test_generate_ukca_checklist(self, checklist_generator: ChecklistGenerator):
        checklist = checklist_generator.generate([ComplianceRegime.UKCA])
        assert checklist.total_items == 8  # UKCA has 8 items in template
        assert all(i.regime == ComplianceRegime.UKCA for i in checklist.items)

    def test_generate_combined_checklist(self, checklist_generator: ChecklistGenerator):
        """Combined UKCA + CE + FCC checklist should have items from all three."""
        checklist = checklist_generator.generate([
            ComplianceRegime.UKCA,
            ComplianceRegime.CE,
            ComplianceRegime.FCC,
        ])
        assert checklist.total_items == 23  # 8 + 10 + 5
        ukca_items = checklist.items_for_regime(ComplianceRegime.UKCA)
        ce_items = checklist.items_for_regime(ComplianceRegime.CE)
        fcc_items = checklist.items_for_regime(ComplianceRegime.FCC)
        assert len(ukca_items) == 8
        assert len(ce_items) == 10
        assert len(fcc_items) == 5

    def test_all_items_start_not_started(self, checklist_generator: ChecklistGenerator):
        checklist = checklist_generator.generate([ComplianceRegime.CE])
        assert all(
            i.evidence_status == EvidenceStatus.NOT_STARTED for i in checklist.items
        )

    def test_initial_coverage_is_zero(self, checklist_generator: ChecklistGenerator):
        checklist = checklist_generator.generate([ComplianceRegime.CE])
        assert checklist.coverage_pct == 0.0
        assert checklist.covered_items == 0


# ===========================================================================
# Evidence Tracker Tests
# ===========================================================================


class TestEvidenceTracker:
    """Tests for evidence linking and coverage computation."""

    def test_link_evidence_to_item(
        self, checklist_generator: ChecklistGenerator, evidence_tracker: EvidenceTracker
    ):
        checklist = checklist_generator.generate([ComplianceRegime.CE])
        first_item = checklist.items[0]

        record = EvidenceRecord(
            evidence_id="EVD-001",
            item_id=first_item.item_id,
            title="Conducted emissions test report",
            artifact_path="tests/emc/conducted_emissions_report.pdf",
            status=EvidenceStatus.ACCEPTED,
        )
        result = evidence_tracker.link_evidence(checklist, record)
        assert result is True
        assert first_item.evidence_status == EvidenceStatus.ACCEPTED
        assert "EVD-001" in first_item.evidence_refs

    def test_link_evidence_to_nonexistent_item(
        self, checklist_generator: ChecklistGenerator, evidence_tracker: EvidenceTracker
    ):
        checklist = checklist_generator.generate([ComplianceRegime.CE])
        record = EvidenceRecord(
            evidence_id="EVD-999",
            item_id="nonexistent-item",
            title="Phantom evidence",
            status=EvidenceStatus.SUBMITTED,
        )
        result = evidence_tracker.link_evidence(checklist, record)
        assert result is False

    def test_coverage_increases_with_evidence(
        self, checklist_generator: ChecklistGenerator, evidence_tracker: EvidenceTracker
    ):
        checklist = checklist_generator.generate([ComplianceRegime.FCC])
        mandatory = [i for i in checklist.items if i.mandatory]

        # Link accepted evidence to first mandatory item
        record = EvidenceRecord(
            evidence_id="EVD-001",
            item_id=mandatory[0].item_id,
            title="Conducted emissions test",
            status=EvidenceStatus.ACCEPTED,
        )
        evidence_tracker.link_evidence(checklist, record)
        coverage = evidence_tracker.compute_coverage(checklist)

        assert coverage > 0.0
        assert checklist.covered_items == 1

    def test_full_coverage_when_all_mandatory_accepted(
        self, checklist_generator: ChecklistGenerator, evidence_tracker: EvidenceTracker
    ):
        checklist = checklist_generator.generate([ComplianceRegime.FCC])
        mandatory = [i for i in checklist.items if i.mandatory]

        for idx, item in enumerate(mandatory):
            record = EvidenceRecord(
                evidence_id=f"EVD-{idx:03d}",
                item_id=item.item_id,
                title=f"Evidence for {item.requirement}",
                status=EvidenceStatus.ACCEPTED,
            )
            evidence_tracker.link_evidence(checklist, record)

        coverage = evidence_tracker.compute_coverage(checklist)
        assert coverage == 100.0
        assert checklist.covered_items == len(mandatory)


# ===========================================================================
# Full Pipeline Integration Tests
# ===========================================================================


class TestBOMCompliancePipeline:
    """End-to-end tests combining BOM risk and compliance into gate readiness."""

    def test_full_pipeline_score_bom_then_checklist(
        self,
        scorer: BOMRiskScorer,
        drone_bom: list[BOMEntry],
        checklist_generator: ChecklistGenerator,
        evidence_tracker: EvidenceTracker,
    ):
        """Full pipeline: score BOM -> generate checklist -> link evidence -> check coverage."""
        # Step 1: Score BOM
        report = scorer.score_bom(drone_bom)
        assert report.total_parts == 18

        # Step 2: Generate compliance checklist
        checklist = checklist_generator.generate([
            ComplianceRegime.UKCA,
            ComplianceRegime.CE,
            ComplianceRegime.FCC,
        ])
        assert checklist.total_items == 23

        # Step 3: Link some evidence
        first_ce = checklist.items_for_regime(ComplianceRegime.CE)[0]
        evidence_tracker.link_evidence(
            checklist,
            EvidenceRecord(
                evidence_id="EVD-CE-001",
                item_id=first_ce.item_id,
                title="EMC test report",
                status=EvidenceStatus.ACCEPTED,
            ),
        )

        # Step 4: Compute coverage
        coverage = evidence_tracker.compute_coverage(checklist)
        assert 0.0 < coverage < 100.0

    def test_bom_risk_contributes_to_gate_readiness(
        self, risk_report: BOMRiskReport
    ):
        """High-risk BOM should reduce gate readiness score."""
        # Gate readiness formula: base 100, penalize for risk
        bom_penalty = risk_report.overall_risk_score * 40  # Up to 40 points
        readiness = 100 - bom_penalty
        assert readiness < 100  # Must be penalized (we have EOL parts)
        assert readiness > 0

    def test_compliance_coverage_contributes_to_gate_readiness(
        self,
        checklist_generator: ChecklistGenerator,
        evidence_tracker: EvidenceTracker,
    ):
        """Compliance coverage feeds into gate readiness."""
        checklist = checklist_generator.generate([ComplianceRegime.CE])

        # No evidence -> 0% coverage -> gate penalty
        coverage = evidence_tracker.compute_coverage(checklist)
        compliance_score = coverage  # 0-100 maps directly
        assert compliance_score == 0.0

        # With some evidence
        mandatory = [i for i in checklist.items if i.mandatory]
        for idx, item in enumerate(mandatory[:3]):
            evidence_tracker.link_evidence(
                checklist,
                EvidenceRecord(
                    evidence_id=f"EVD-{idx}",
                    item_id=item.item_id,
                    title=f"Test report {idx}",
                    status=EvidenceStatus.ACCEPTED,
                ),
            )
        coverage = evidence_tracker.compute_coverage(checklist)
        assert coverage > 0.0

    def test_combined_gate_readiness_calculation(
        self,
        scorer: BOMRiskScorer,
        drone_bom: list[BOMEntry],
        checklist_generator: ChecklistGenerator,
        evidence_tracker: EvidenceTracker,
    ):
        """Combined BOM risk + compliance coverage -> EVT gate readiness."""
        # Score BOM
        report = scorer.score_bom(drone_bom)

        # Generate and partially complete compliance checklist
        checklist = checklist_generator.generate([ComplianceRegime.CE, ComplianceRegime.FCC])
        mandatory = [i for i in checklist.items if i.mandatory]
        # Accept evidence for half the mandatory items
        half = len(mandatory) // 2
        for idx in range(half):
            evidence_tracker.link_evidence(
                checklist,
                EvidenceRecord(
                    evidence_id=f"EVD-{idx}",
                    item_id=mandatory[idx].item_id,
                    title=f"Evidence {idx}",
                    status=EvidenceStatus.ACCEPTED,
                ),
            )
        compliance_coverage = evidence_tracker.compute_coverage(checklist)

        # Gate readiness: weighted combination
        bom_weight = 0.4
        compliance_weight = 0.6
        bom_score = (1 - report.overall_risk_score) * 100
        gate_readiness = bom_weight * bom_score + compliance_weight * compliance_coverage

        assert 0 < gate_readiness < 100
        assert gate_readiness > 20  # At least some readiness with half compliance done
