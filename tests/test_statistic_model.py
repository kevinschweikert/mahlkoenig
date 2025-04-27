from mahlkoenig.models import parse_statistics

VALID_PAYLOAD = """
X54ExportIdentification;
ExportSessionId;27
ExportTimestamp;1970-07-27T20:47:53
GrinderName;X54Grinder
ProductNo;HEM-E54-HMI-P02.115
SerialNo;1777D6
Type;StatisticData

X54StatisticData;
SystemRestarts;27
TotalGrindShots;1235
TotalGrindTime;130027
Recipe1GrindShots;14
Recipe1GrindTime;1536
Recipe2GrindShots;7
Recipe2GrindTime;826
Recipe3GrindShots;4
Recipe3GrindTime;262
Recipe4GrindShots;0
Recipe4GrindTime;0
ManualModeGrindShots;204
ManualModeGrindTime;17711
DiscLifeTime;130027
TotalOnTime;817259
StandbyTime;812608
TotalMotorOnTime;130027
TotalErrors01;22
TotalErrors02;28
TotalErrors03;0
TotalErrors04;0
TotalErrors08;0
TotalErrors09;0
TotalErrors10;0
"""


def test_parse_statistics():
    """Test that a valid payload gets parsed into a statistic model"""

    stats = parse_statistics(VALID_PAYLOAD)

    assert stats.system_restarts == 27
    assert stats.total_grind_shots == 1235
    assert stats.total_grind_time.total_seconds() == 130027
    assert stats.recipe_1_grind_shots == 14
    assert stats.recipe_1_grind_time.total_seconds() == 1536
    assert stats.recipe_2_grind_shots == 7
    assert stats.recipe_2_grind_time.total_seconds() == 826
    assert stats.recipe_3_grind_shots == 4
    assert stats.recipe_3_grind_time.total_seconds() == 262
    assert stats.recipe_4_grind_shots == 0
    assert stats.recipe_4_grind_time.total_seconds() == 0
    assert stats.manual_mode_grind_shots == 204
    assert stats.manual_mode_grind_time.total_seconds() == 17711
    assert stats.disc_life_time.total_seconds() == 130027
    assert stats.total_on_time.total_seconds() == 817259
    assert stats.standby_time.total_seconds() == 812608
    assert stats.total_motor_on_time.total_seconds() == 130027
    assert stats.total_errors_01 == 22
    assert stats.total_errors_02 == 28
    assert stats.total_errors_03 == 0
    assert stats.total_errors_04 == 0
    assert stats.total_errors_08 == 0
    assert stats.total_errors_09 == 0
    assert stats.total_errors_10 == 0
