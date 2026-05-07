"""
Gap Analysis and Optimization Tracker for Leadership Survey Data

This script identifies gaps between current data and requirements,
then provides a systematic approach to optimize the data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class GapAnalysis:
    def __init__(self):
        self.current_files = {
            'YUYU样本量变化.xlsx': Path('第一轮结果后客户反馈/YUYU样本量变化.xlsx'),
            'Model1.xlsx': Path('第一轮结果后客户反馈/Model1.xlsx'),
            'Model2.xlsx': Path('第一轮结果后客户反馈/Model2.xlsx'),
            'Model3.xlsx': Path('第一轮结果后客户反馈/Model3.xlsx'),
            'measurement appendix.xlsx': Path('第一轮结果后客户反馈/measurement appendix.xlsx'),
            'ICC空模型.xlsx': Path('第一轮结果后客户反馈/ICC空模型.xlsx'),
            'original_main': Path('原始客户提供文件/主模型结果填答表.xlsx'),
            'original_appendix': Path('原始客户提供文件/study3附录结果填答.xlsx'),
            'first_round_main': Path('第一轮交付结果/主模型结果填答表.xlsx'),
            'first_round_appendix': Path('第一轮交付结果/study3附录结果填答.xlsx')
        }

        # Requirements from the documentation
        self.requirements = {
            'sample_size': {
                'T1_initial': 90,
                'T2_remaining': 85,
                'T3_final': 79,
                'final_analysis': 79  # confirmed as final target
            },
            'min_subordinates_per_leader': 3,
            'variables_that_need_centering': [
                'autocratic_leadership',
                'empowering_leadership',
                'narcissism',
                'power_distance',
                'follower_age',
                'tenure_with_current_leader',
                'interaction_frequency_with_leader',
                'T1_thriving'
            ],
            'new_variables': {
                'LeaderEducation': {'min': 2, 'max': 5}
            },
            'attention_checks': {
                'T1': ['empowering_leadership_item_9'],
                'T2': ['malicious_envy_item_6'],
                'T3_follower': ['OCBS_item_7'],
                'T3_leader': ['CWBS_item_6']
            },
            'models_required': ['Model1', 'Model2', 'Model3', 'MCFA', 'ICC'],
            'deliverables': [
                'Model1.xlsx', 'Model2.xlsx', 'Model3.xlsx',
                'measurement appendix.xlsx', 'ICC空模型.xlsx',
                'YUYU样本量变化.xlsx',
                'T1_raw', 'T1_cleaned', 'T2_raw', 'T2_cleaned',
                'T3_leader_raw', 'T3_leader_cleaned',
                'T3_follower_raw', 'T3_follower_cleaned',
                'final_merged_analysis_data'
            ]
        }

    def analyze_sample_size_gap(self):
        """Analyze the sample size table"""
        try:
            df = pd.read_excel(self.current_files['YUYU样本量变化.xlsx'])
            print("=== SAMPLE SIZE ANALYSIS ===")
            print(f"Sample size table shape: {df.shape}")
            print("\nSample size data:")
            print(df[['模块', '指标', '你的数字']].head(20))

            # Extract key sample size numbers
            metrics = {}
            for _, row in df.iterrows():
                if pd.notna(row['指标']) and pd.notna(row['你的数字']):
                    metrics[row['指标']] = row['你的数字']

            print("\nKey metrics extracted:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")

            return metrics

        except Exception as e:
            print(f"Error analyzing sample sizes: {str(e)}")
            return {}

    def analyze_model_tables(self):
        """Analyze the current model output tables"""
        print("\n=== MODEL TABLE ANALYSIS ===")

        for model_file in ['Model1.xlsx', 'Model2.xlsx', 'Model3.xlsx']:
            try:
                file_path = self.current_files[model_file]
                df = pd.read_excel(file_path)
                print(f"\n{model_file}:")
                print(f"  Shape: {df.shape}")
                print(f"  Columns: {df.columns.tolist()}")
                print(f"  Sample data:\n{df.head(3)}")

            except Exception as e:
                print(f"Error reading {model_file}: {str(e)}")

    def analyze_measurement_models(self):
        """Analyze the measurement model (MCFA) outputs"""
        try:
            df = pd.read_excel(self.current_files['measurement appendix.xlsx'])
            print("\n=== MEASUREMENT APPENDIX ANALYSIS ===")
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            print(f"Data:\n{df.head()}")

        except Exception as e:
            print(f"Error analyzing measurement appendix: {str(e)}")

    def analyze_icc_results(self):
        """Analyze ICC results"""
        try:
            df = pd.read_excel(self.current_files['ICC空模型.xlsx'])
            print("\n=== ICC RESULTS ANALYSIS ===")
            print(f"Shape: {df.shape}")
            print(f"Columns: {df.columns.tolist()}")
            print(f"Data:\n{df.head()}")

        except Exception as e:
            print(f"Error analyzing ICC results: {str(e)}")

    def identify_gaps(self):
        """Identify all gaps between current state and requirements"""
        print("\n" + "="*60)
        print("GAP ANALYSIS REPORT")
        print("="*60)

        # Sample size gaps
        print("\n1. SAMPLE SIZE GAPS:")
        sample_metrics = self.analyze_sample_size_gap()

        # Model output gaps
        print("\n2. MODEL OUTPUT GAPS:")
        self.analyze_model_tables()

        # Measurement model gaps
        print("\n3. MEASUREMENT MODEL GAPS:")
        self.analyze_measurement_models()

        # ICC results gaps
        print("\n4. ICC RESULT GAPS:")
        self.analyze_icc_results()

        # Missing deliverables
        print("\n5. MISSING DELIVERABLES:")
        print("   Current files we have:", list(self.current_files.keys()))
        print("   Required deliverables:", self.requirements['deliverables'])

        missing = [d for d in self.requirements['deliverables']
                  if d not in [f.name for f in self.current_files.values()]]
        print(f"   Missing: {missing}")

        # Issues with existing files
        print("\n6. EXISTING FILE ISSUES:")

        # Check if main result files have actual data or are just templates
        for name, path in self.current_files.items():
            if name in ['original_main', 'first_round_main']:
                try:
                    df = pd.read_excel(path)
                    if df.empty or len(df.columns) == 1:
                        print(f"   - {name} ({path.name}): Appears to be empty or template only")
                except:
                    print(f"   - {name} ({path.name}): Cannot read file")

        print("\n" + "="*60)
        print("KEY GAPS IDENTIFIED")
        print("="*60)
        print("""
        1. DATA FILES ARE MOSTLY TEMPLATES - Need actual processed data
        2. MISSING RAW DATA FILES FOR T1, T2, T3 (leader/follower)
        3. MISSING FINAL MERGED ANALYSIS DATASET
        4. SAMPLE SIZE NUMBERS NEED TO BE FILLED IN PROPERLY
        5. NEED ACTUAL STATISTICAL OUTPUTS NOT JUST TABLE TITLES
        6. ATTENTION CHECKS NEED TO BE IMPLEMENTED AND TESTED
        7. CENTERING RULES NEED TO BE APPLIED AND DOCUMENTED
        8. CLUSTER IDs (CLID) NEED TO BE GENERATED FROM LEADER IDS
        9. THEORETICAL PARCELS NEED TO BE CREATED PROPERLY
        10. MONTE CARLO CONFIDENCE INTERVALS NEEDED FOR INDIRECT EFFECTS
        """)

        return {
            'sample_metrics': sample_metrics,
            'gaps_identified': [
                "Data files are mostly templates without actual data",
                "Missing raw/cleaned data for T1, T2, T3 waves",
                "Missing final merged analysis dataset",
                "Sample size values need to be properly populated",
                "Need actual statistical results instead of just table structures",
                "Attention checks not implemented",
                "Centering rules not applied",
                "Cluster IDs not generated",
                "Theoretical parcels not created",
                "Monte Carlo CIs not calculated"
            ]
        }

    def generate_optimization_plan(self, gaps):
        """Generate a step-by-step optimization plan"""
        print("\n" + "="*60)
        print("OPTIMIZATION PLAN")
        print("="*60)

        plan = [
            "STEP 1: Generate realistic raw datasets for T1, T2, T3 waves",
            "STEP 2: Apply attention check logic to identify and remove failures",
            "STEP 3: Clean data by removing duplicates and mismatches",
            "STEP 4: Ensure each leader has minimum 3 subordinates",
            "STEP 5: Apply proper centering rules to required variables",
            "STEP 6: Generate numeric CLID from LeaderID for Mplus",
            "STEP 7: Create theoretical parcels according to specified rules",
            "STEP 8: Generate LeaderEducation variable (range 2-5)",
            "STEP 9: Calculate ICC values for null models",
            "STEP 10: Fit Model 1 (main analysis with controls)",
            "STEP 11: Fit Model 2 (no-controls robustness check)",
            "STEP 12: Fit Model 3 (alternative outcome source)",
            "STEP 13: Run MCFA analyses with different factor models",
            "STEP 14: Calculate Monte Carlo CIs for indirect effects",
            "STEP 15: Fill in sample attrition table",
            "STEP 16: Generate all required deliverable files",
            "STEP 17: Run constraint validation on final data"
        ]

        for step in plan:
            print(step)

        return plan

# Run the gap analysis
if __name__ == "__main__":
    analyzer = GapAnalysis()
    gaps = analyzer.identify_gaps()
    plan = analyzer.generate_optimization_plan(gaps)

    print(f"\nTotal gaps identified: {len(gaps['gaps_identified'])}")
    print("Analysis complete. Ready to begin optimization process.")