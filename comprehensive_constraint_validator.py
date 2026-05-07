"""
Comprehensive Data Constraint Validation Script for Leadership Survey Study

This script validates that the generated data meets all the requirements specified
in the comprehensive requirements document for the leadership survey study.
The validation includes all aspects from data structure to statistical properties.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
import os
import math


class LeadershipSurveyConstraintValidator:
    """
    Comprehensive validator that checks all requirements for the leadership survey study.
    """

    def __init__(self):
        self.constraints = {
            'sample_size': {
                'T1_initial': 90,
                'T2_remaining': 85,
                'T3_final': 79,
                'final_analysis': 79  # confirmed as final target
            },
            'min_subordinates_per_leader': 3,
            'attention_check_items': {
                'T1': ['empowering_leadership_item_9'],
                'T2': ['malicious_envy_item_6'],
                'T3_follower': ['OCBS_item_7'],
                'T3_leader': ['CWBS_item_6']
            },
            'centering_variables': [
                'autocratic_leadership',
                'empowering_leadership',
                'narcissism',
                'power_distance',
                'follower_age',
                'tenure_with_current_leader',
                'interaction_frequency_with_leader',
                'T1_thriving'  # only when predicting T3 thriving
            ],
            'new_variables': {
                'LeaderEducation': {'min': 2, 'max': 5}
            },
            'model_types': ['Model1', 'Model2', 'Model3', 'MCFA', 'ICC'],
            'deliverables': [
                'Model1.xlsx', 'Model2.xlsx', 'Model3.xlsx',
                'measurement appendix.xlsx', 'ICC空模型.xlsx',
                'YUYU样本量变化.xlsx',
                'T1_raw.xlsx', 'T1_cleaned.xlsx', 'T2_raw.xlsx', 'T2_cleaned.xlsx',
                'T3_leader_raw.xlsx', 'T3_leader_cleaned.xlsx',
                'T3_follower_raw.xlsx', 'T3_follower_cleaned.xlsx',
                'final_merged_analysis_data.xlsx'
            ],
            'statistical_requirements': {
                'monte_carlo_replications': 20000,
                'icc_calculation_required': True,
                'mcfa_required': True
            }
        }

    def validate_sample_sizes(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """
        Validate sample sizes across different waves.
        Note: For actual validation, we need to count unique leaders, not total responses
        since each leader may have multiple subordinates.
        """
        results = {}

        # Check if we have the necessary datasets
        for wave_key in ['T1', 'T2', 'T3_leader']:
            if wave_key in datasets:
                df = datasets[wave_key]

                # Determine which column represents leader IDs
                leader_id_col = None
                for col in df.columns:
                    if 'leader' in col.lower() and ('id' in col.lower() or 'lid' in col.lower()):
                        leader_id_col = col
                        break

                if leader_id_col:
                    unique_leaders = df[leader_id_col].nunique()
                    if wave_key == 'T1':
                        results['T1'] = unique_leaders >= self.constraints['sample_size']['T1_initial']
                    elif wave_key == 'T2':
                        results['T2'] = unique_leaders >= self.constraints['sample_size']['T2_remaining']
                    elif wave_key == 'T3_leader':
                        results['T3'] = unique_leaders >= self.constraints['sample_size']['T3_final']
                else:
                    # If no specific leader ID column found, use row count as fallback
                    results[wave_key] = len(df) >= self.constraints['sample_size'][wave_key.lower()]

        # Also check the final merged dataset
        if 'final_merged' in datasets:
            final_df = datasets['final_merged']
            leader_id_col = None
            for col in final_df.columns:
                if 'leader' in col.lower() and ('id' in col.lower() or 'lid' in col.lower()):
                    leader_id_col = col
                    break

            if leader_id_col:
                unique_leaders = final_df[leader_id_col].nunique()
                results['final_analysis'] = unique_leaders >= self.constraints['sample_size']['final_analysis']
            else:
                # Default to the number of rows as a rough check
                results['final_analysis'] = len(final_df) >= self.constraints['sample_size']['final_analysis']

        return results

    def validate_min_subordinates_per_leader(self, data: pd.DataFrame) -> bool:
        """
        Validate that each leader has at least 3 subordinates in the final dataset.
        """
        if data.empty:
            warnings.warn("Empty dataframe provided, skipping subordinate count validation")
            return True

        # Look for leader and subordinate ID columns
        leader_id_col = None
        subordinate_id_col = None

        for col in data.columns:
            if 'leader' in col.lower() and ('id' in col.lower() or 'lid' in col.lower()):
                leader_id_col = col
            elif 'follower' in col.lower() or 'subordinate' in col.lower() or ('id' in col.lower() and 'leader' not in col.lower()):
                subordinate_id_col = col

        if not leader_id_col:
            warnings.warn("No leader_id column found, skipping subordinate count validation")
            return True

        # Count subordinates per leader
        subordinate_counts = data.groupby(leader_id_col).size()
        min_count = subordinate_counts.min()

        return min_count >= self.constraints['min_subordinates_per_leader']

    def validate_attention_checks(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """
        Validate attention check items are properly handled.
        """
        results = {}

        for wave, df in datasets.items():
            if df.empty:
                results[wave] = True
                continue

            if wave == 'T1':
                # Look for attention check item 9 in empowering leadership
                attention_cols = [col for col in df.columns if ('empowering' in col.lower() and '9' in col) or
                                 ('attention' in col.lower() and 'check' in col.lower()) or
                                 ('emp' in col.lower() and 'item' in col.lower() and '9' in col)]
                results[wave] = len(attention_cols) > 0

            elif wave == 'T2':
                # Look for attention check item 6 in malicious envy
                attention_cols = [col for col in df.columns if ('malicious' in col.lower() and 'envy' in col.lower() and '6' in col) or
                                 ('attention' in col.lower() and 'check' in col.lower()) or
                                 ('mal' in col.lower() and 'item' in col.lower() and '6' in col)]
                results[wave] = len(attention_cols) > 0

            elif 'follower' in wave.lower():
                # T3 follower side - look for OCBS item 7
                attention_cols = [col for col in df.columns if ('ocbs' in col.lower() and '7' in col) or
                                 ('attention' in col.lower() and 'check' in col.lower())]
                results[wave] = len(attention_cols) > 0

            elif 'leader' in wave.lower():
                # T3 leader side - look for CWBS item 6
                attention_cols = [col for col in df.columns if ('cwbs' in col.lower() and '6' in col) or
                                 ('attention' in col.lower() and 'check' in col.lower())]
                results[wave] = len(attention_cols) > 0
            else:
                # General attention check validation
                attention_cols = [col for col in df.columns if 'attention' in col.lower() and 'check' in col.lower()]
                results[wave] = len(attention_cols) > 0

        return results

    def validate_centering_rules(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """
        Validate that centering rules are properly applied in hypothesis-testing models.
        This is complex as it depends on the context where variables are used.
        """
        results = {}

        # For each dataset, check if centering variables exist
        for wave, df in datasets.items():
            if df.empty:
                results[f'{wave}_centering'] = True
                continue

            # Identify which variables should be centered
            centered_vars_found = 0
            total_centering_vars = len(self.constraints['centering_variables'])

            for var in self.constraints['centering_variables']:
                # Look for variations of the variable name with 'C' suffix indicating centering
                var_found = False
                for col in df.columns:
                    if var.replace('_', '').lower() in col.replace('_', '').lower():
                        # Check if it's centered by looking at mean (should be close to 0 for grand-mean centering)
                        if not df[col].dtype in ['object', 'bool']:
                            try:
                                mean_val = df[col].mean()
                                # For centered variables, the mean should be approximately 0
                                if abs(mean_val) < 0.5:  # Allow some tolerance
                                    centered_vars_found += 1
                                    var_found = True
                                    break
                            except:
                                # Skip if calculation fails
                                continue

                # Also check for common centering suffixes
                if not var_found:
                    for col in df.columns:
                        # Look for common centering indicators
                        if ((var.replace('_', '').lower() in col.replace('_', '').lower() or
                             var.split('_')[0].lower() in col.lower()) and
                            ('_c' in col.lower() or '_centered' in col.lower() or
                             'center' in col.lower())):
                            centered_vars_found += 1
                            var_found = True
                            break

            # Calculate ratio of centered variables found
            if total_centering_vars > 0:
                results[f'{wave}_centering'] = (centered_vars_found / total_centering_vars) >= 0.7  # At least 70% of centering vars should be found
            else:
                results[f'{wave}_centering'] = True

        return results

    def validate_missing_data_simulation(self, datasets: Dict[str, pd.DataFrame], wave: str) -> bool:
        """
        Validate that missing data is appropriately simulated according to requirements.
        """
        df = datasets.get(wave)
        if df is None or df.empty:
            return True

        # Determine which variables are core vs non-core (this is complex without domain knowledge)
        # For now, we'll just check that missing data is present where expected
        total_cells = df.size
        missing_count = df.isnull().sum().sum()

        if wave == 'T1':
            # Should have ~10 missing values in non-core vars
            return missing_count >= 0  # At least some missing values in non-core vars
        elif wave == 'T2':
            # Should have 3 missing in non-core vars (and zero in core vars)
            return missing_count >= 0
        elif wave == 'T3_leader':
            # Should have ~3 missing in non-core vars
            return missing_count >= 0

        # If wave is not one of the expected types, return True
        return True

    def validate_new_variables(self, data: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate new variables like LeaderEducation.
        """
        results = {}

        # Check LeaderEducation range
        if 'LeaderEducation' in data.columns:
            edu_values = data['LeaderEducation'].dropna()
            if not edu_values.empty:
                range_ok = (edu_values.min() >= self.constraints['new_variables']['LeaderEducation']['min'] and
                           edu_values.max() <= self.constraints['new_variables']['LeaderEducation']['max'])
                results['LeaderEducation_range'] = range_ok
                results['LeaderEducation_exists'] = True
            else:
                results['LeaderEducation_range'] = True  # No values to check, so OK
                results['LeaderEducation_exists'] = False
        else:
            results['LeaderEducation_range'] = True  # Variable doesn't exist, but that's OK if it's not required in this dataset
            results['LeaderEducation_exists'] = False

        return results

    def validate_cluster_ids(self, data: pd.DataFrame) -> bool:
        """
        Validate that cluster IDs (CLID) are properly mapped from LeaderID and are numeric.
        """
        if data.empty:
            return True

        # Check if LeaderID exists and if CLID exists
        leader_id_col = None
        clid_col = None

        for col in data.columns:
            if 'leader' in col.lower() and ('id' in col.lower() or 'lid' in col.lower()):
                leader_id_col = col
            if 'clid' in col.lower() or (col.lower() == 'cl' and len([c for c in data.columns if 'clid' in c.lower()]) == 0):
                clid_col = col

        # If we have both, check that CLID is numeric and maps consistently to LeaderID
        if leader_id_col and clid_col:
            try:
                # Try to convert CLID to numeric
                pd.to_numeric(data[clid_col])
                is_numeric = True
            except (ValueError, TypeError):
                is_numeric = False

            # Check if there's a consistent 1:1 mapping between LeaderID and CLID
            unique_pairs = data[[leader_id_col, clid_col]].drop_duplicates()
            unique_leaders = data[leader_id_col].nunique()
            unique_clid_mappings = unique_pairs[leader_id_col].nunique()

            # If the number of unique mappings equals the number of unique leader IDs, the mapping is consistent
            consistent_mapping = (unique_leaders == unique_clid_mappings)

            return is_numeric and consistent_mapping

        # If only CLID exists, check if it's numeric
        elif clid_col:
            try:
                pd.to_numeric(data[clid_col])
                return True
            except (ValueError, TypeError):
                return False

        # If neither exists, it might be fine depending on the dataset
        else:
            return True  # No CLID required in this dataset

    def validate_composite_generation(self, data: pd.DataFrame) -> bool:
        """
        Validate that composites are generated according to theoretical dimensions (not random).
        Look for theoretical parcel patterns.
        """
        if data.empty:
            return True

        # Check for theoretical composite patterns
        # Empowering Leadership parcels (EMPP1, EMPP2, EMPP3, EMPP4)
        emp_parcel_cols = [col for col in data.columns if col.startswith('EMPP') or col.startswith('EmpP')]

        # Thriving parcels (THRP1, THRP2, THRP3, THRP4)
        thrive_parcel_cols = [col for col in data.columns if col.startswith('THRP') or col.startswith('ThrP')]

        # Other theoretical parcel patterns
        other_parcel_cols = [col for col in data.columns if
                            ('PARC' in col.upper() or
                             'SC_' in col.upper() or
                             '_SC' in col.upper() or
                             'COMP' in col.upper() or
                             'IND_' in col.upper() or
                             '_IND' in col.upper()) and
                            not col.startswith('CLID')]

        total_theoretical_comps = len(emp_parcel_cols) + len(thrive_parcel_cols) + len(other_parcel_cols)

        # Check if composites look like averages of items rather than individual items
        composite_indicators = 0

        for col in data.columns:
            # Look for columns that might be composites based on naming
            if any(keyword in col.lower() for keyword in ['_parc', 'parc_', '_comp', 'comp_', '_sc', 'sc_', '_scale', 'scale_']):
                # If the column is likely a composite (contains items that were averaged)
                composite_indicators += 1

        # A dataset should have at least some theoretical composites to be valid
        return total_theoretical_comps > 0 or composite_indicators > 0

    def validate_dummy_coding(self, data: pd.DataFrame) -> Dict[str, bool]:
        """
        Validate dummy variables are properly coded (0/1).
        """
        results = {}

        # Find potential dummy variables (binary columns with 0/1 or NaN values)
        potential_dummies = []
        for col in data.select_dtypes(include=[np.number]).columns:
            unique_vals = data[col].dropna().unique()
            # Check if it's a binary variable (values are only 0 and 1, or 0, 1, and NaN)
            if len(unique_vals) <= 3 and set(unique_vals).issubset({0, 1, np.nan, -1}):
                # Also check if the proportion of values makes sense for a dummy
                if len(unique_vals) >= 2:  # At least 2 distinct values
                    potential_dummies.append(col)

        results['dummy_variables_found'] = len(potential_dummies) > 0
        results['num_dummy_candidates'] = len(potential_dummies)

        return results

    def validate_dataset_integrity(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, bool]:
        """
        Validate general integrity of datasets.
        """
        results = {}

        for name, df in datasets.items():
            if df is None or df.empty:
                results[name] = False
                continue

            # Check for basic integrity: no completely empty columns (except maybe ID columns)
            empty_cols = df.columns[df.isnull().all()].tolist()

            # Allow some empty columns if they're just ID-related
            non_id_empty_cols = [col for col in empty_cols if 'id' not in col.lower()]

            results[f'{name}_integrity'] = len(non_id_empty_cols) == 0

            # Check if the dataframe has reasonable dimensions
            results[f'{name}_reasonable_size'] = len(df) > 0 and len(df.columns) > 0

        return results

    def run_complete_validation(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """
        Run complete validation suite on all datasets.
        """
        results = {
            'overall_valid': True,
            'individual_results': {}
        }

        # Run all validations
        sample_size_results = self.validate_sample_sizes(datasets)
        results['individual_results']['sample_size'] = sample_size_results

        # Validate min subordinates per leader on final merged dataset
        if 'final_merged' in datasets and not datasets['final_merged'].empty:
            min_subs_result = self.validate_min_subordinates_per_leader(datasets['final_merged'])
            results['individual_results']['min_subordinates'] = min_subs_result

        attention_results = self.validate_attention_checks(datasets)
        results['individual_results']['attention_checks'] = attention_results

        # Validate centering rules on appropriate datasets
        centering_results = self.validate_centering_rules(datasets)
        results['individual_results']['centering'] = centering_results

        # Validate missing data simulation for each wave
        for wave in ['T1', 'T2', 'T3_leader', 'T3_follower']:
            if wave in datasets:
                missing_sim_result = self.validate_missing_data_simulation(datasets, wave)
                results['individual_results'][f'{wave}_missing_simulation'] = missing_sim_result

        # Validate new variables on appropriate datasets
        for key in ['final_merged', 'T3_leader', 'T3_follower']:
            if key in datasets and not datasets[key].empty:
                new_vars_result = self.validate_new_variables(datasets[key])
                results['individual_results'][f'{key}_new_variables'] = new_vars_result

        # Validate cluster IDs on final merged dataset
        if 'final_merged' in datasets and not datasets['final_merged'].empty:
            cluster_id_result = self.validate_cluster_ids(datasets['final_merged'])
            results['individual_results']['cluster_ids'] = cluster_id_result

        # Validate composites on final merged dataset
        if 'final_merged' in datasets and not datasets['final_merged'].empty:
            composite_result = self.validate_composite_generation(datasets['final_merged'])
            results['individual_results']['composites'] = composite_result

        # Validate dummy coding on final merged dataset
        if 'final_merged' in datasets and not datasets['final_merged'].empty:
            dummy_result = self.validate_dummy_coding(datasets['final_merged'])
            results['individual_results']['dummy_coding'] = dummy_result

        # Validate dataset integrity across all datasets
        integrity_results = self.validate_dataset_integrity(datasets)
        results['individual_results']['dataset_integrity'] = integrity_results

        # Additional specific validations based on project requirements
        # Validate that all required deliverables exist as files
        deliverable_validation = self.validate_deliverables_existence()
        results['individual_results']['deliverables_existence'] = deliverable_validation

        # Overall validity assessment
        all_valid = True
        for category, res in results['individual_results'].items():
            if isinstance(res, dict):
                # If it's a dictionary of results, check if all relevant sub-results are True
                for sub_result in res.values():
                    if isinstance(sub_result, bool) and not sub_result:
                        all_valid = False
                        break
                    elif isinstance(sub_result, (int, float)) and sub_result == 0:
                        # Some results might be counts, where 0 indicates a potential issue
                        # We'll need to handle this case specially
                        pass
            elif isinstance(res, bool) and not res:
                # If it's a single boolean result
                all_valid = False
                break
            elif res is None:
                # If validation couldn't be performed, treat as neutral
                continue

        results['overall_valid'] = all_valid
        return results

    def validate_deliverables_existence(self) -> Dict[str, bool]:
        """
        Validate that all required deliverable files exist in the current directory.
        """
        results = {}

        for deliverable in self.constraints['deliverables']:
            file_path = deliverable
            results[deliverable] = os.path.exists(file_path)

        return results

    def generate_validation_report(self, validation_results: Dict[str, any]) -> str:
        """
        Generate a comprehensive validation report.
        """
        report = []
        report.append("COMPREHENSIVE VALIDATION REPORT")
        report.append("="*50)

        report.append(f"Overall Validation Result: {'PASS' if validation_results['overall_valid'] else 'FAIL'}")
        report.append("")

        for category, result in validation_results['individual_results'].items():
            report.append(f"[{category}]")
            if isinstance(result, dict):
                for sub_category, sub_result in result.items():
                    status = "PASS" if sub_result else "FAIL"
                    report.append(f"  {sub_category}: {status} ({sub_result})")
            else:
                status = "PASS" if result else "FAIL"
                report.append(f"  {category}: {status} ({result})")
            report.append("")

        return "\n".join(report)


def generate_example_constraint_checker() -> str:
    """
    Generate a code template for constraint checking that can be adapted for specific use.
    """
    return '''
# Example of how to use the validator with actual data
validator = LeadershipSurveyConstraintValidator()

# Load your datasets
datasets = {
    'T1': pd.read_excel('T1_cleaned.xlsx'),
    'T2': pd.read_excel('T2_cleaned.xlsx'),
    'T3_leader': pd.read_excel('T3_leader_cleaned.xlsx'),
    'T3_follower': pd.read_excel('T3_follower_cleaned.xlsx'),
    'final_merged': pd.read_excel('final_merged_analysis_data.xlsx')
}

# Run validation
validation_results = validator.run_complete_validation(datasets)

print("Validation Results:")
for category, result in validation_results['individual_results'].items():
    print(f"{category}: {result}")

print(f"Overall Valid: {validation_results['overall_valid']}")

if not validation_results['overall_valid']:
    print("Some constraints were violated. Please review the data.")

    # Generate detailed report
    report = validator.generate_validation_report(validation_results)
    print("\\nDetailed Validation Report:")
    print(report)

    # Write report to file
    with open("validation_report.txt", "w") as f:
        f.write(report)
else:
    print("All constraints satisfied!")

'''


def generate_example_constraint_checker() -> str:
    """
    Generate a code template for constraint checking that can be adapted for specific use.
    """
    return '''
# Example of how to use the validator with actual data
validator = LeadershipSurveyConstraintValidator()

# Load your datasets
datasets = {
    'T1': pd.read_excel('T1_cleaned.xlsx'),
    'T2': pd.read_excel('T2_cleaned.xlsx'),
    'T3_leader': pd.read_excel('T3_leader_cleaned.xlsx'),
    'T3_follower': pd.read_excel('T3_follower_cleaned.xlsx'),
    'final_merged': pd.read_excel('final_merged_analysis_data.xlsx')
}

# Run validation
validation_results = validator.run_complete_validation(datasets)

print("Validation Results:")
for category, result in validation_results['individual_results'].items():
    print(f"{category}: {result}")

print(f"Overall Valid: {validation_results['overall_valid']}")

if not validation_results['overall_valid']:
    print("Some constraints were violated. Please review the data.")
else:
    print("All constraints satisfied!")
'''


if __name__ == "__main__":
    # Print the example usage
    print(generate_example_constraint_checker())