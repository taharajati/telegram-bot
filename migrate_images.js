// migrate_images.js - Node.js version (uses built-in fetch)
// Migration script: Download all product images from Telegram and store locally.

const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');

// Config
const DATABASE_URL = process.env.DATABASE_URL || 'postgresql://foroshgram:foroshgram_secure_2024@postgres:5432/foroshgram';
const BOT_TOKEN = process.env.BOT_TOKEN;
const STORAGE_DIR = path.join('/app', 'storage', 'products');

if (!fs.existsSync(STORAGE_DIR)) {
  fs.mkdirSync(STORAGE_DIR, { recursive: true });
}

async function downloadImage(fileId) {
  if (!fileId) return null;
  
  try {
    // Step 1: Get file path
    const getFileRes = await fetch(
      `https://api.telegram.org/bot${BOT_TOKEN}/getFile?file_id=${encodeURIComponent(fileId)}`
    );
    const getFileData = await getFileRes.json();
    
    if (!getFileData.ok) {
      console.log(`  ❌ getFile failed for ${fileId.substring(0, 20)}...: ${getFileData.description}`);
      return null;
    }
    
    const filePath = getFileData.result.file_path;
    
    // Step 2: Download file
    const fileRes = await fetch(`https://api.telegram.org/file/bot${BOT_TOKEN}/${filePath}`);
    if (!fileRes.ok) {
      console.log(`  ❌ Download failed for ${filePath}: HTTP ${fileRes.status}`);
      return null;
    }
    
    const buffer = await fileRes.arrayBuffer();
    return Buffer.from(buffer);
  } catch (err) {
    console.log(`  ❌ Error downloading ${fileId.substring(0, 20)}...: ${err.message}`);
    return null;
  }
}

async function main() {
  if (!BOT_TOKEN) {
    console.error('❌ BOT_TOKEN not set');
    process.exit(1);
  }
  
  console.log('🔄 Connecting to database...');
  const pool = new Pool({ connectionString: DATABASE_URL });
  
  try {
    // Get all products with image_file_id
    const result = await pool.query(`
      SELECT id, image_file_id 
      FROM products 
      WHERE image_file_id IS NOT NULL AND image_file_id != ''
    `);
    
    const products = result.rows;
    console.log(`📦 Found ${products.length} products with images`);
    
    for (let i = 0; i < products.length; i++) {
      const product = products[i];
      const pid = product.id;
      const fileId = product.image_file_id;
      
      // Determine extension
      const ext = '.jpg';
      const localPath = path.join(STORAGE_DIR, `${pid}${ext}`);
      const localUrl = `/storage/products/${pid}${ext}`;
      
      // Skip if already exists
      if (fs.existsSync(localPath)) {
        console.log(`  [${i+1}/${products.length}] ✅ Product ${pid}: already exists`);
        continue;
      }
      
      console.log(`  [${i+1}/${products.length}] ⬇️  Downloading product ${pid}...`);
      const imageData = await downloadImage(fileId);
      
      if (imageData) {
        fs.writeFileSync(localPath, imageData);
        
        // Update database with local URL
        await pool.query(
          'UPDATE products SET image_url = $1 WHERE id = $2',
          [localUrl, pid]
        );
        console.log(`     ✅ Saved: ${pid}${ext} (${imageData.length} bytes)`);
      } else {
        console.log(`     ❌ Failed to download`);
      }
      
      // Rate limit
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    console.log('🎉 Migration complete!');
  } catch (err) {
    console.error('❌ Error:', err);
  } finally {
    await pool.end();
  }
}

main();