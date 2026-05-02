/**
 * Lightweight interface verification script
 * Checks plugin interface compatibility without requiring OpenClaw SDK
 */

import fs from 'fs';
import ts from 'typescript';

// Read the TypeScript source file
const sourceCode = fs.readFileSync('./index.ts', 'utf8');
const sourceFile = ts.createSourceFile(
  'index.ts',
  sourceCode,
  ts.ScriptTarget.Latest,
  true
);

console.log('🔍 Verifying Cognix Plugin Interface Compatibility...\n');

let hasErrors = false;

// Check 1: Verify memory_store uses 'text' parameter
function checkMemoryStoreParams() {
  console.log('1. Checking memory_store parameters...');
  
  const findMemoryStore = (node) => {
    if (ts.isPropertyAssignment(node) && node.name.getText() === 'memory_store') {
      // Find parameters object
      const paramsProp = node.initializer.properties.find(
        p => p.name.getText() === 'parameters'
      );
      
      if (paramsProp) {
        const properties = paramsProp.initializer.properties;
        const hasText = properties.some(p => p.name.getText() === 'text');
        const hasContent = properties.some(p => p.name.getText() === 'content');
        const hasUserId = properties.some(p => p.name.getText() === 'userId');
        
        if (hasText && !hasContent && hasUserId) {
          console.log('✅ PASS: memory_store uses "text" parameter (not "content") and has userId');
          return;
        }
      }
      
      console.log('❌ FAIL: memory_store parameters incorrect');
      hasErrors = true;
    }
    
    ts.forEachChild(node, findMemoryStore);
  };
  
  findMemoryStore(sourceFile);
}

// Check 2: Verify all tools have userId parameter
function checkAllToolsHaveUserId() {
  console.log('\n2. Checking all tools have userId parameter...');
  
  const toolNames = ['memory_search', 'memory_store', 'memory_list', 'memory_get', 'memory_forget'];
  const toolsFound = {};
  
  const findTools = (node) => {
    if (ts.isPropertyAssignment(node) && toolNames.includes(node.name.getText())) {
      const toolName = node.name.getText();
      toolsFound[toolName] = true;
      
      const paramsProp = node.initializer.properties.find(
        p => p.name.getText() === 'parameters'
      );
      
      if (paramsProp) {
        const hasUserId = paramsProp.initializer.properties.some(
          p => p.name.getText() === 'userId'
        );
        
        if (hasUserId) {
          console.log(`✅ ${toolName} has userId parameter`);
        } else {
          console.log(`❌ ${toolName} missing userId parameter`);
          hasErrors = true;
        }
      }
    }
    
    ts.forEachChild(node, findTools);
  };
  
  findTools(sourceFile);
  
  // Check all required tools exist
  toolNames.forEach(name => {
    if (!toolsFound[name]) {
      console.log(`❌ Missing required tool: ${name}`);
      hasErrors = true;
    }
  });
}

// Check 3: Verify session support exists
function checkSessionSupport() {
  console.log('\n3. Checking session memory support...');
  
  // Check for currentSessionId variable
  const hasSessionId = sourceCode.includes('let currentSessionId: string | undefined;');
  
  // Check for sessionKey usage
  const hasSessionKey = sourceCode.includes('context?.sessionKey');
  
  // Check for run_id with currentSessionId
  const hasRunId = sourceCode.includes('run_id: currentSessionId');
  
  if (hasSessionId && hasSessionKey && hasRunId) {
    console.log('✅ PASS: Session memory support is implemented');
  } else {
    console.log('❌ FAIL: Session memory support incomplete');
    hasErrors = true;
  }
}

// Check 4: Verify memory_store return structure
function checkMemoryStoreReturn() {
  console.log('\n4. Checking memory_store return structure...');
  
  const sourceLines = sourceCode.split('\n');
  let inMemoryStore = false;
  let foundReturn = false;
  
  for (let i = 0; i < sourceLines.length; i++) {
    const line = sourceLines[i];
    
    if (line.includes('name: "memory_store"') || line.includes('memory_store: {')) {
      inMemoryStore = true;
    }
    
    if (inMemoryStore && line.includes('return {')) {
      // Check next lines for expected properties
      const returnLines = sourceLines.slice(i, i + 10).join('\n');
      const hasContent = returnLines.includes('content:');
      const hasAdded = returnLines.includes('added:');
      const hasUpdated = returnLines.includes('updated:');
      const hasResults = returnLines.includes('results:');
      
      if (hasContent && hasAdded && hasUpdated && hasResults) {
        console.log('✅ PASS: memory_store returns structured result with added/updated counts');
        foundReturn = true;
        break;
      }
    }
    
    if (inMemoryStore && line.includes('},')) {
      inMemoryStore = false;
    }
  }
  
  if (!foundReturn) {
    console.log('❌ FAIL: memory_store return structure incorrect');
    hasErrors = true;
  }
}

// Check 5: Verify openclaw.plugin.json exists and is valid
function checkPluginJson() {
  console.log('\n5. Checking openclaw.plugin.json...');
  
  try {
    const pluginJson = JSON.parse(fs.readFileSync('./openclaw.plugin.json', 'utf8'));
    
    const requiredFields = ['id', 'description', 'kind', 'uiHints', 'configSchema'];
    const missingFields = requiredFields.filter(field => !pluginJson[field]);
    
    if (missingFields.length === 0 && pluginJson.kind === 'memory') {
      console.log('✅ PASS: openclaw.plugin.json is valid and has correct structure');
    } else {
      console.log(`❌ FAIL: openclaw.plugin.json missing fields: ${missingFields.join(', ')}`);
      hasErrors = true;
    }
    
    // Check required config fields
    if (pluginJson.configSchema?.required?.includes('apiKey')) {
      console.log('✅ PASS: configSchema requires apiKey');
    } else {
      console.log('❌ FAIL: configSchema missing required apiKey field');
      hasErrors = true;
    }
    
  } catch (e) {
    console.log('❌ FAIL: openclaw.plugin.json is invalid or missing');
    hasErrors = true;
  }
}

// Run all checks
checkMemoryStoreParams();
checkAllToolsHaveUserId();
checkSessionSupport();
checkMemoryStoreReturn();
checkPluginJson();

console.log('\n' + '='.repeat(50));
if (!hasErrors) {
  console.log('🎉 All interface checks passed! Plugin is compatible with Mem0 interface.');
  console.log('📋 Next steps: Test with running Cognix service to verify end-to-end functionality.');
} else {
  console.log('❌ Some checks failed. Please fix the issues above.');
  process.exit(1);
}
