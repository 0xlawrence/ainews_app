# Citation System Fix Report

## Problem Analysis

The citation system was generating completely unrelated citations, violating PRD F-15. Specifically:

- **Example Issue**: A ChatGPT search guide article was incorrectly citing Anthropic economic programs and Meta hiring news
- **Root Cause**: Articles with different topic domains were being clustered together due to loose similarity thresholds and insufficient semantic validation

## Identified Issues

### 1. Clustering Algorithm Problems
- **File**: `/src/utils/topic_clustering.py`
- **Issue**: `multi_source_detection` threshold was too low (0.75), allowing loosely related articles to cluster
- **Issue**: No domain-specific semantic validation beyond embedding similarity
- **Issue**: Articles from different business domains (HR vs Research vs Economics) were grouped together

### 2. Citation Validation Gaps  
- **File**: `/src/utils/citation_generator.py`
- **Issue**: `_validate_citation_relevance` function relied on keyword matching rather than semantic domain understanding
- **Issue**: Specific company/topic combinations like "Meta research" vs "LinkedIn hiring" weren't properly blocked
- **Issue**: Missing systematic domain incompatibility checks

### 3. Settings Configuration
- **File**: `/src/constants/settings.py`
- **Issue**: Similarity thresholds were too permissive for quality citation generation

## Implemented Fixes

### Fix 1: Raised Clustering Threshold
**Location**: `/src/constants/settings.py:36`

```python
# BEFORE
'multi_source_detection': 0.75, # Multi-source topic detection

# AFTER  
'multi_source_detection': 0.85, # Multi-source topic detection (CRITICAL: raised to 0.85 to prevent unrelated article grouping)
```

**Impact**: More stringent similarity requirements for clustering articles together.

### Fix 2: Enhanced Citation Domain Validation
**Location**: `/src/utils/citation_generator.py`

Added new method `_validate_same_topic_domain()` that:
- Defines 6 distinct topic domains (HR/Recruitment, Research/Technical, Economic/Policy, etc.)
- Checks for mutually exclusive domain pairs  
- Blocks citations between incompatible domains (e.g., HR vs Research)
- Uses comprehensive keyword matching for domain classification

**Key Domain Definitions**:
```python
topic_domains = {
    'hr_recruitment': ['hiring', 'recruitment', '採用', '人材', 'linkedin', '求人', 'massive offers'],
    'research_technical': ['research', 'researcher', '研究', '技術', 'model', 'poaches', 'scientists'],
    'economic_policy': ['economy', 'economic', '経済', '失業', '雇用喪失', 'futures program'],
    'business_finance': ['investment', 'funding', 'ipo', 'valuation', '投資', 'venture'],
    'product_tools': ['cli', 'api', 'tool', 'product', '製品', 'feature'],
    'local_infrastructure': ['ollama', 'local', 'ローカル', 'infrastructure']
}
```

### Fix 3: Enhanced Incompatible Citation Detection
**Location**: `/src/utils/citation_generator.py:1596`

Enhanced `_is_incompatible_citation()` with:
- Domain-based incompatibility checks
- Specific pattern blocking for Meta vs LinkedIn
- Topic category validation (HR vs Research vs Economics)
- Bidirectional incompatibility checking

### Fix 4: Topic Clustering Domain Coherence
**Location**: `/src/utils/topic_clustering.py`

Added `_validate_topic_domain_coherence()` method that:
- Validates cluster coherence before similarity calculations
- Prevents articles from different domains being clustered together
- Uses the same domain definitions as citation validation for consistency

### Fix 5: Enhanced Citation Relevance Validation
**Location**: `/src/utils/citation_generator.py:1810`

Updated `_validate_citation_relevance()` to:
- Call domain validation first before other checks
- Use enhanced topic conflict detection
- Add specific blocking for Meta vs LinkedIn combinations
- Include bidirectional conflict checking

## Test Results

Created comprehensive tests that validate:

✅ **Meta research vs LinkedIn hiring**: Correctly blocked (Domain exclusion: research_technical vs hr_recruitment)

✅ **Economic policy vs hiring offers**: Correctly blocked (Domain exclusion: economic_policy vs hr_recruitment)  

✅ **OpenAI model vs OpenAI API**: Correctly allowed (Same domain: research_technical)

✅ **Incompatible patterns**: All correctly identified and blocked

✅ **Valid citations**: Properly allowed through validation

## Specific Case Resolution

**Original Problem**:
- Main Article: "ChatGPT検索術：OpenAIが教える！質問を分割、精度50%向上"  
- Wrong Citation: Anthropic economic program + Meta hiring news

**How Fixed**:
1. **Domain Classification**: ChatGPT guide → `product_tools` domain
2. **Economic program** → `economic_policy` domain  
3. **Meta hiring** → `hr_recruitment` domain
4. **Domain Exclusion**: All three domains are incompatible, citations blocked
5. **Result**: Only relevant, same-domain articles will be cited

## Performance Impact

- **Clustering**: Slight increase in processing time due to domain validation, but prevents incorrect clusters
- **Citation Generation**: Minor overhead for domain checking, but dramatically improves relevance
- **Memory**: Minimal impact from additional validation logic
- **Quality**: Significant improvement in citation relevance and user experience

## Monitoring Recommendations

1. **Track Citation Relevance**: Monitor feedback on citation quality
2. **Cluster Quality**: Check clustering accuracy with domain validation
3. **False Negatives**: Ensure valid citations aren't being blocked unnecessarily
4. **Threshold Tuning**: May need to adjust 0.85 threshold based on production data

## Files Modified

1. `/src/constants/settings.py` - Raised similarity threshold
2. `/src/utils/citation_generator.py` - Enhanced validation logic  
3. `/src/utils/topic_clustering.py` - Added domain coherence validation

These fixes ensure that citations are topically relevant and prevent the PRD F-15 violation of unrelated article citations.