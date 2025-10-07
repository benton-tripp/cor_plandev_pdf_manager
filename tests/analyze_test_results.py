import pandas as pd
import os

TEST_RESULTS = "tests/outputs/optimize_results_20251007_101541.csv"

def analyze_test_results(file_path, top_n=5):
    """
    Analyze PDF optimization test results to find the best savings with no quality/content loss.
    
    Args:
        file_path: Path to the CSV results file
        top_n: Number of top results to display
    """
    
    if not os.path.exists(file_path):
        print(f"ERROR: Results file not found: {file_path}")
        return
    
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} test results from {os.path.basename(file_path)}")
        
        # Filter for successful optimizations only
        successful_df = df[df['success'] == True].copy()
        print(f"Found {len(successful_df)} successful optimizations")
        
        if len(successful_df) == 0:
            print("ERROR: No successful optimizations found!")
            return
        
        # Define quality/content preservation criteria
        preservation_columns = [
            'text_content_preserved', 'metadata_preserved', 'annotations_preserved',
            'images_preserved', 'widgets_preserved', 'drawings_preserved',
            'signature_fields_preserved', 'content_streams_preserved',
            'optional_content_preserved', 'signature_text_preserved', 'stamp_text_preserved'
        ]
        
        # Filter for high-quality optimizations (all preservation criteria met)
        # First, separate tests that have preservation data from those that don't
        has_preservation_data = successful_df.copy()
        for col in preservation_columns:
            if col in has_preservation_data.columns:
                has_preservation_data = has_preservation_data[has_preservation_data[col].notna()]
        
        print(f"Found {len(has_preservation_data)} tests with preservation data")
        
        if len(has_preservation_data) > 0:
            # Filter for high-quality optimizations among those with data
            quality_filter = True
            for col in preservation_columns:
                if col in has_preservation_data.columns:
                    # Only check preservation for tests that have the data
                    quality_filter = quality_filter & (
                        (has_preservation_data[col] == True) | 
                        (has_preservation_data[col] == 'True')
                    )
            
            high_quality_df = has_preservation_data[quality_filter].copy()
            print(f"Found {len(high_quality_df)} high-quality optimizations with no content loss")
            
            if len(high_quality_df) >= top_n:
                analysis_df = high_quality_df
                print("Using high-quality optimizations with preservation data")
            else:
                # If not enough high-quality results, combine with other successful tests
                other_tests = successful_df[~successful_df.index.isin(has_preservation_data.index)]
                analysis_df = pd.concat([high_quality_df, other_tests]).head(max(top_n * 2, 20))
                print(f"Combined {len(high_quality_df)} high-quality with other tests (total: {len(analysis_df)})")
        else:
            print("WARNING: No tests with preservation data found!")
            print("Using all successful optimizations...")
            analysis_df = successful_df
        
        # Find the top n largest savings with no quality/content loss
        print(f"\nFinding top {top_n} largest savings with no quality/content loss:")
        print("=" * 80)
        
        # Sort by size_change_percent (most negative = biggest savings)
        # Use nsmallest because negative percentages represent size reductions
        top_savings = analysis_df.nsmallest(top_n, 'size_change_percent', keep='all')
        
        if len(top_savings) == 0:
            print("ERROR: No savings found!")
            return
        
        for i, (idx, row) in enumerate(top_savings.iterrows(), 1):
            print(f"\nRANK {i}: {row['optimization_method'].upper()}")
            print("-" * 40)
            
            # Basic optimization info
            print(f"File: {row['input_file']}")
            print(f"Method: {row['optimization_method']} ({row['optimization_params']})")
            print(f"Test Type: {row['test_type']}")
            
            # Size reduction details
            size_change_kb = row.get('size_change_kb', 0)
            size_change_percent = row.get('size_change_percent', 0)
            print(f"Size Change: {size_change_kb:+.2f} KB ({size_change_percent:+.2f}%)")
            print(f"Before: {row['input_size_kb']:.2f} KB → After: {row['output_size_kb']:.2f} KB")
            
            # Objects reduction
            objects_change = row.get('objects_change', 0)
            print(f"Objects: {row['input_objects']} → {row['output_objects']} (Change: {objects_change:+d})")
            
            # Content analysis
            print(f"\nCONTENT ANALYSIS:")
            print(f"   Text: {row.get('input_text_length', 'N/A')} chars")
            print(f"   Annotations: {row.get('input_annotations', 'N/A')}")
            print(f"   Images: {row.get('input_images', 'N/A')} (Small: {row.get('input_small_images', 'N/A')})")
            print(f"   Form Fields: {row.get('input_widgets', 'N/A')}")
            print(f"   Signature Fields: {row.get('input_signature_fields', 'N/A')}")
            print(f"   Vector Drawings: {row.get('input_drawings', 'N/A')}")
            print(f"   Content Streams: {row.get('input_content_streams', 'N/A')}")
            print(f"   Fonts: {row.get('input_fonts', 'N/A')}")
            
            # Special content indicators
            special_content = []
            if row.get('input_has_signature_text', False):
                special_content.append("Digital Signature Text")
            if row.get('input_has_stamp_text', False):
                special_content.append("Stamp/Approval Text")
            if row.get('input_encrypted', False):
                special_content.append("Encrypted")
            if special_content:
                print(f"   Special Content: {', '.join(special_content)}")
            
            # Quality preservation check
            print(f"\nCONTENT PRESERVATION:")
            preservation_status = []
            missing_data = []
            
            for col in preservation_columns:
                if col in row:
                    if pd.notna(row[col]):
                        status = row[col]
                        if status in [True, 'True']:
                            preservation_status.append(f"PRESERVED: {col.replace('_preserved', '').replace('_', ' ').title()}")
                        elif status in [False, 'False']:
                            preservation_status.append(f"LOST: {col.replace('_preserved', '').replace('_', ' ').title()}")
                        else:
                            missing_data.append(col.replace('_preserved', '').replace('_', ' ').title())
                    else:
                        missing_data.append(col.replace('_preserved', '').replace('_', ' ').title())
                else:
                    missing_data.append(col.replace('_preserved', '').replace('_', ' ').title())
            
            if preservation_status:
                for status in preservation_status:
                    print(f"   {status}")
            
            if missing_data:
                if len(missing_data) == len(preservation_columns):
                    print("   No preservation analysis performed for this test type")
                    print("   (Individual optimization tests don't include detailed preservation tracking)")
                else:
                    print(f"   Missing preservation data for: {', '.join(missing_data)}")
            
            if not preservation_status and not missing_data:
                print("   No preservation data available")
            
            # Additional notes
            if pd.notna(row.get('notes', '')):
                print(f"\nNotes: {row['notes']}")
            
            # Compression analysis
            if row.get('already_compressed', False):
                print(f"WARNING: Already Compressed - This PDF was already well-compressed")
            
            print("=" * 40)
        
        # Summary statistics
        print(f"\nSUMMARY STATISTICS:")
        print(f"   Average Size Reduction: {analysis_df['size_change_percent'].mean():.2f}%")
        print(f"   Best Single Reduction: {analysis_df['size_change_percent'].min():.2f}%")
        print(f"   Average Objects Reduced: {analysis_df['objects_change'].mean():.1f}")
        
        # Method effectiveness
        print(f"\nMETHOD EFFECTIVENESS:")
        method_stats = analysis_df.groupby('optimization_method')['size_change_percent'].agg(['count', 'mean', 'min']).round(2)
        method_stats.columns = ['Tests', 'Avg_Reduction_%', 'Best_Reduction_%']
        method_stats = method_stats.sort_values('Avg_Reduction_%')
        print(method_stats.to_string())
        
        return analysis_df
        
    except Exception as e:
        print(f"ERROR analyzing results: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_best_method_for_content_type(file_path):
    """
    Analyze which optimization methods work best for different content types.
    """
    
    try:
        df = pd.read_csv(file_path)
        successful_df = df[df['success'] == True].copy()
        
        print(f"\nBEST METHODS BY CONTENT TYPE:")
        print("=" * 60)
        
        # Analyze by content characteristics
        content_types = {
            'High Annotation Count': successful_df['input_annotations'] > 5,
            'Many Images': successful_df['input_images'] > 10,
            'Large Text Content': successful_df['input_text_length'] > 10000,
            'Has Signature Fields': successful_df['input_signature_fields'] > 0,
            'Many Drawings': successful_df['input_drawings'] > 100,
            'Has Stamp Text': successful_df['input_has_stamp_text'] == True,
            'Has Signature Text': successful_df['input_has_signature_text'] == True
        }
        
        for content_type, condition in content_types.items():
            subset = successful_df[condition]
            if len(subset) > 0:
                best_method = subset.loc[subset['size_change_percent'].idxmin()]
                print(f"\n{content_type}:")
                print(f"   Best Method: {best_method['optimization_method']}")
                print(f"   Best Reduction: {best_method['size_change_percent']:.2f}%")
                print(f"   File: {best_method['input_file']}")
        
    except Exception as e:
        print(f"ERROR in content type analysis: {e}")

def compare_aggressive_vs_conservative(file_path):
    """
    Compare aggressive vs conservative optimization results.
    """
    
    try:
        df = pd.read_csv(file_path)
        
        conservative = df[df['optimization_method'] == 'conservative']
        aggressive = df[df['optimization_method'] == 'aggressive']
        
        if len(conservative) > 0 and len(aggressive) > 0:
            print(f"\nAGGRESSIVE vs CONSERVATIVE COMPARISON:")
            print("=" * 50)
            
            print(f"Conservative:")
            print(f"   Avg Reduction: {conservative['size_change_percent'].mean():.2f}%")
            print(f"   Success Rate: {(conservative['success'].sum() / len(conservative) * 100):.1f}%")
            
            print(f"Aggressive:")
            print(f"   Avg Reduction: {aggressive['size_change_percent'].mean():.2f}%")
            print(f"   Success Rate: {(aggressive['success'].sum() / len(aggressive) * 100):.1f}%")
            
            # Content preservation comparison
            preservation_cols = ['text_content_preserved', 'annotations_preserved', 'images_preserved']
            
            for method_name, method_df in [('Conservative', conservative), ('Aggressive', aggressive)]:
                if len(method_df) > 0:
                    preserved_count = 0
                    total_checks = 0
                    for col in preservation_cols:
                        if col in method_df.columns:
                            preserved = method_df[col].sum() if method_df[col].dtype == bool else (method_df[col] == True).sum()
                            total = len(method_df[method_df[col].notna()])
                            preserved_count += preserved
                            total_checks += total
                    
                    if total_checks > 0:
                        preservation_rate = (preserved_count / total_checks) * 100
                        print(f"   Content Preservation: {preservation_rate:.1f}%")
        
    except Exception as e:
        print(f"ERROR in comparison: {e}")

if __name__ == "__main__":
    print("PDF Optimization Results Analyzer")
    print("=" * 50)
    
    # Use the default test results file or allow override
    import sys
    results_file = sys.argv[1] if len(sys.argv) > 1 else TEST_RESULTS
    
    # Convert to absolute path if relative
    if not os.path.isabs(results_file):
        results_file = os.path.join(os.path.dirname(__file__), '..', results_file)
        results_file = os.path.normpath(results_file)
    
    print(f"Analyzing: {results_file}")
    
    # Main analysis
    analysis_df = analyze_test_results(results_file, top_n=5)
    
    if analysis_df is not None:
        # Additional analyses
        find_best_method_for_content_type(results_file)
        compare_aggressive_vs_conservative(results_file)
        
        # File location reminder
        print(f"\nFull results available at: {results_file}")
    else:
        print("ERROR: Analysis failed!")
        sys.exit(1)