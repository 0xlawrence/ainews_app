# 🖼️ Image Embedding Feature Guide

This guide covers the complete image embedding functionality implemented in Phase 5.

## 🎯 Overview

The AI News Newsletter Generator now automatically fetches, optimizes, and embeds images from articles to create visually appealing newsletters. Images are hosted on Supabase Storage and embedded responsively in the final Markdown output.

## ✨ Features

### 🎬 **YouTube Video Support**
- Automatic thumbnail extraction from YouTube URLs
- Multiple quality levels: `maxresdefault` → `hqdefault` → `mqdefault` → `default`
- Click-to-play video previews with custom styling
- YouTube-specific metadata and labeling

### 🌐 **OGP Image Support**
- Open Graph Protocol image extraction from web articles
- Fallback to first suitable image on page if no OGP image
- Support for PNG, JPEG, WebP formats

### ⚡ **Image Optimization**
- Automatic PNG→JPEG conversion with transparency handling
- Intelligent resizing (default: 600px width)
- File size compression (default: <500KB)
- Unique filename generation with timestamps

### ☁️ **Cloud Storage**
- Supabase Storage integration with public URL generation
- Automatic bucket management and configuration
- CDN-optimized image delivery

## 🏗️ Architecture

### Components

1. **`ImageFetcher`** (`src/utils/image_fetcher.py`)
   - Multi-strategy image acquisition
   - YouTube ID extraction and thumbnail fetching
   - OGP meta tag parsing
   - Error handling and retries

2. **`ImageUploader`** (`src/utils/image_uploader.py`) 
   - Supabase Storage integration
   - Image optimization and conversion
   - Public URL generation
   - Metadata tracking

3. **`ImageProcessor`** (`src/utils/image_processor.py`)
   - Unified pipeline combining fetch + upload
   - Concurrent processing for multiple articles
   - Comprehensive error handling

4. **Workflow Integration** (`src/workflow/newsletter_workflow.py`)
   - `process_images_node` added to LangGraph workflow
   - Positioned between `cluster_topics` and `generate_newsletter`
   - Graceful failure handling

### Data Flow

```
Article URL → ImageFetcher → Temp File → ImageUploader → Supabase Storage → Public URL → Newsletter Template
```

## 🚀 Quick Start

### 1. Prerequisites

Ensure you have the required dependencies:
```bash
pip install Pillow beautifulsoup4 requests lxml
```

### 2. Supabase Setup

#### Option A: Automatic Setup
```bash
python3 create_supabase_bucket_v2.py
```

#### Option B: Manual Setup
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Navigate to Storage → Create bucket
3. Name: `ainews-images`
4. Public: ✅ Yes
5. File size limit: 500KB (optional)

### 3. Environment Variables

Required in your `.env` file:
```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_role_key
```

### 4. Test the Setup

```bash
# Test image fetching only
python3 test_real_image_processing.py

# Test complete upload pipeline
python3 test_youtube_upload.py

# Run E2E tests
python3 test_e2e_image_workflow.py
```

## 🎨 Newsletter Template Integration

### Automatic Image Embedding

Images are automatically embedded in newsletters using responsive HTML:

#### YouTube Videos
```html
<div style="margin: 16px 0;">
  <a href="https://youtube.com/watch?v=VIDEO_ID" target="_blank">
    <img src="SUPABASE_PUBLIC_URL" alt="ARTICLE_TITLE" 
         style="width: 100%; max-width: 600px; height: auto; 
                border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
  </a>
  <p style="margin: 8px 0 0 0; font-size: 14px; color: #666;">
    📺 YouTube動画 - クリックして視聴
  </p>
</div>
```

#### Regular Articles
```html
<div style="margin: 16px 0;">
  <img src="SUPABASE_PUBLIC_URL" alt="ARTICLE_TITLE" 
       style="width: 100%; max-width: 600px; height: auto; 
              border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
</div>
```

### Template Customization

To modify image display, edit `src/templates/daily_newsletter.jinja2`:

```jinja2
{%- if article.image_url %}
{%- if article.image_metadata and article.image_metadata.source_type == 'youtube' %}
<!-- YouTube-specific rendering -->
{%- else %}
<!-- Regular image rendering -->
{%- endif %}
{%- endif %}
```

## 🔧 Configuration

### Image Processing Settings

Default settings in `src/utils/image_processor.py`:

```python
DEFAULT_MAX_WIDTH = 600      # pixels
DEFAULT_MAX_SIZE_KB = 500    # kilobytes
DEFAULT_CONCURRENT = 5       # max parallel processing
```

### Supabase Storage Settings

Configure in `src/config/settings.py`:

```python
supabase_image_bucket: str = Field(
    default="ainews-images", 
    env="SUPABASE_IMAGE_BUCKET"
)
```

### Workflow Settings

Image processing can be controlled via workflow configuration:

```python
# Disable image processing
workflow_state['skip_images'] = True

# Custom concurrency
workflow_state['image_concurrency'] = 3
```

## 🧪 Testing & Debugging

### Test Scripts

1. **Basic Functionality**: `test_e2e_image_workflow.py`
   - Tests workflow integration
   - Validates data models
   - Checks template rendering

2. **Real Image Processing**: `test_real_image_processing.py`
   - Tests actual image fetching
   - Validates Supabase configuration

3. **YouTube Pipeline**: `test_youtube_upload.py`
   - End-to-end YouTube image processing
   - Upload and public URL generation

### Debug Logs

Enable detailed logging:

```python
import logging
logging.getLogger('src.utils.image_processor').setLevel(logging.DEBUG)
```

Check workflow logs:
```bash
tail -f logs/newsletter_$(date +%Y-%m-%d).json
```

### Common Issues

#### 1. Supabase Bucket Not Found
```
Error: {"statusCode":"404","error":"Bucket not found"}
```
**Solution**: Run `python3 create_supabase_bucket_v2.py`

#### 2. Image Fetch Failures
```
Error: No suitable image found for URL
```
**Solutions**:
- Check if URL is accessible
- Verify OGP tags exist
- Try different user-agent strings

#### 3. Upload Failures
```
Error: Failed to upload image to Supabase
```
**Solutions**:
- Verify SUPABASE_KEY permissions
- Check bucket public settings
- Validate image file format

## 🎯 Best Practices

### Performance Optimization

1. **Concurrent Processing**: Process multiple images in parallel
```python
max_concurrent = min(5, len(articles))
semaphore = asyncio.Semaphore(max_concurrent)
```

2. **Lazy Initialization**: Initialize image processor only when needed
```python
if self.image_processor is None:
    self.image_processor = ImageProcessor()
```

3. **Graceful Degradation**: Newsletter generation continues without images
```python
try:
    image_url = await process_image(url)
except Exception as e:
    logger.warning(f"Image processing failed: {e}")
    image_url = None
```

### Error Handling

1. **Multi-Strategy Fetching**: Try multiple image sources
2. **Timeout Management**: Set reasonable timeouts for fetches
3. **Size Validation**: Check file sizes before processing
4. **Format Validation**: Ensure valid image formats

### Resource Management

1. **Temporary File Cleanup**: Always clean up temp files
2. **Memory Management**: Process images in batches
3. **Storage Limits**: Monitor Supabase storage usage
4. **API Rate Limits**: Respect external site rate limits

## 📊 Monitoring & Analytics

### Metrics to Track

1. **Success Rate**: Percentage of articles with images
2. **Processing Time**: Average time per image
3. **Storage Usage**: Total Supabase storage consumed
4. **Error Rates**: Failed fetch/upload rates

### Logging

Image processing logs include:
- Processing time per article
- Success/failure rates
- Error details and stack traces
- Storage URLs and metadata

### Performance Monitoring

```bash
# Check recent image processing logs
grep "Image processing" logs/newsletter_*.json | tail -20

# Monitor storage usage
curl -H "Authorization: Bearer $SUPABASE_KEY" \
     "$SUPABASE_URL/storage/v1/bucket/ainews-images"
```

## 🔮 Future Enhancements

### Planned Features

1. **Advanced OGP Generation**: Custom image generation for articles without images
2. **Image Caching**: Local cache for frequently accessed images
3. **CDN Integration**: Enhanced delivery via external CDN
4. **Image Analytics**: Track view counts and engagement
5. **Bulk Operations**: Batch processing for historical articles

### Performance Improvements

1. **WebP Support**: Next-gen image format for better compression
2. **Adaptive Quality**: Dynamic quality based on image content
3. **Progressive Loading**: Lazy loading for large newsletters
4. **Thumbnail Generation**: Multiple sizes for different devices

---

**Last Updated**: 2025-07-06  
**Version**: Phase 5 Complete  
**Status**: Production Ready ✅