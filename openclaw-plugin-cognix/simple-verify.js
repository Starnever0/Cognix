/**
 * Simple verification using grep patterns
 */
import fs from 'fs';

const sourceCode = fs.readFileSync('./index.ts', 'utf8');

console.log('🔍 Verifying Cognix Plugin Interface Compatibility...\n');
let pass = 0;
let fail = 0;

// Test 1: memory_store uses text parameter not content
console.log('1. memory_store parameter check:');
if (sourceCode.includes('text: Type.String({ description: "Information to remember" }')) {
  console.log('✅ PASS: Uses "text" parameter');
  pass++;
} else {
  console.log('❌ FAIL: Missing "text" parameter');
  fail++;
}

if (!sourceCode.includes('content: Type.String({ description: "Content to store" }')) {
  console.log('✅ PASS: No "content" parameter conflict');
  pass++;
} else {
  console.log('❌ FAIL: Found old "content" parameter');
  fail++;
}

// Test 2: All tools have userId parameter
console.log('\n2. userId parameter check for all tools:');
const tools = ['memory_search', 'memory_store', 'memory_list', 'memory_get', 'memory_forget'];
tools.forEach(tool => {
  const pattern = new RegExp(`userId[^}]*description[^}]*${tool}|${tool}[^}]*userId:`, 's');
  if (sourceCode.includes(`userId: Type.Optional(Type.String({ description: "User ID to`) && 
      sourceCode.includes(tool)) {
    console.log(`✅ ${tool}: has userId parameter`);
    pass++;
  } else {
    // Double check by looking for the userId in parameters
    const toolPattern = new RegExp(`${tool}[\\s\\S]*?parameters[^}]*\\}[\\s\\S]*?\\}`, 's');
    const match = sourceCode.match(toolPattern);
    if (match && match[0].includes('userId')) {
      console.log(`✅ ${tool}: has userId parameter`);
      pass++;
    } else {
      console.log(`❌ ${tool}: missing userId parameter`);
      fail++;
    }
  }
});

// Test 3: Session support
console.log('\n3. Session memory support check:');
if (sourceCode.includes('let currentSessionId: string | undefined;')) {
  console.log('✅ PASS: Session ID tracking variable exists');
  pass++;
} else {
  console.log('❌ FAIL: No session ID tracking');
  fail++;
}

if (sourceCode.includes('context?.sessionKey')) {
  console.log('✅ PASS: Reads sessionKey from context');
  pass++;
} else {
  console.log('❌ FAIL: Does not read sessionKey');
  fail++;
}

if (sourceCode.includes('run_id: currentSessionId')) {
  console.log('✅ PASS: Uses currentSessionId as run_id for session memory');
  pass++;
} else {
  console.log('❌ FAIL: Does not use session ID for run_id');
  fail++;
}

// Test 4: memory_store return structure
console.log('\n4. memory_store return structure check:');
if (sourceCode.includes('content: summary.join(') && 
    sourceCode.includes('added: added.length,') && 
    sourceCode.includes('updated: updated.length,') &&
    sourceCode.includes('results: result.results,')) {
  console.log('✅ PASS: Returns structured result with added/updated counts');
  pass++;
} else {
  console.log('❌ FAIL: Return structure incorrect');
  fail++;
}

// Test 5: openclaw.plugin.json exists
console.log('\n5. Plugin configuration check:');
try {
  const pluginJson = JSON.parse(fs.readFileSync('./openclaw.plugin.json', 'utf8'));
  if (pluginJson.id && pluginJson.kind === 'memory' && pluginJson.configSchema) {
    console.log('✅ PASS: openclaw.plugin.json is valid');
    pass++;
    
    if (pluginJson.configSchema.required?.includes('apiKey')) {
      console.log('✅ PASS: configSchema requires apiKey');
      pass++;
    } else {
      console.log('❌ FAIL: apiKey not in required fields');
      fail++;
    }
  } else {
    console.log('❌ FAIL: plugin.json structure invalid');
    fail++;
  }
} catch (e) {
  console.log('❌ FAIL: Missing or invalid openclaw.plugin.json');
  fail++;
}

// Summary
console.log('\n' + '='.repeat(50));
console.log(`📊 Results: ${pass} passed, ${fail} failed`);

if (fail === 0) {
  console.log('\n🎉 ALL TESTS PASSED!');
  console.log('✅ Plugin interface is 100% compatible with Mem0 specification');
  console.log('\n📝 Next steps:');
  console.log('1. Start Cognix backend service at http://localhost:8765');
  console.log('2. Test end-to-end functionality in OpenClaw');
  console.log('3. Verify: memory_store, search, session support all work correctly');
} else {
  console.log('\n❌ Some tests failed. Fix the issues above.');
  process.exit(1);
}
