const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../pelican-web/index.html'), 'utf8');
const context = vm.createContext({ D: { repos: [] }, document: { getElementById() { return output; } } });
const output = { innerHTML: '' };
const mediaCode = html.slice(html.indexOf('function mediaTag('), html.indexOf('function groups('));
const codeCode = html.slice(html.indexOf('function drawCode('), html.indexOf('function drawSources('));
const escapeCode = html.match(/^function esc\(.*$/m)[0];
vm.runInContext(escapeCode + '\n' + mediaCode + '\n' + codeCode, context);

test('a webpage or YouTube address must not be rendered as a broken image', () => {
  for (const url of ['https://tihuqiche.com', 'https://www.youtube.com/live/abc?t=10']) {
    context.url = url;
    const rendered = vm.runInContext('mediaTag(url)', context);
    assert.doesNotMatch(rendered, /<img|<object/);
    assert.match(rendered, /href=/);
  }
});

test('text-only records explain the absence of an attachment', () => {
  context.item = { id: 'text', model: 'comment', media: '', mediaStatus: 'text-only', mediaNote: '原帖未附图片或视频' };
  const rendered = vm.runInContext('card(item, "time")', context);
  assert.match(rendered, /原帖未附图片或视频/);
  assert.doesNotMatch(rendered, /no figure|class="frame"/i);
});

test('source archives and demos have usable local links', () => {
  context.D.repos = [{ title: 'sample', url: 'https://example.com/', zip: 'repos/sample.zip', demo: 'demos/sample.html' }];
  vm.runInContext('drawCode()', context);
  assert.match(output.innerHTML, /href="repos\/sample.zip"/);
  assert.match(output.innerHTML, /href="demos\/sample.html"/);
});

test('video thumbnails retain their source poster and avoid full preloading', () => {
  const rendered = vm.runInContext('mediaTag("media/a.mp4", {poster:"media/a.jpg"})', context);
  assert.match(rendered, /poster="media\/a.jpg"/);
  assert.match(rendered, /preload="none"/);
});

test('deleted upstream shares are clearly marked rather than advertised as playable', () => {
  context.item = { id: 'deleted', media: '', mediaStatus: 'source-deleted', mediaNote: '原对话已被删除', externalMediaUrl: 'https://example.com/share' };
  const rendered = vm.runInContext('card(item, "time")', context);
  assert.match(rendered, /来源已删除/);
  assert.doesNotMatch(rendered, /在线演示/);
});

test('detail view includes every attachment with its provenance', () => {
  context.item = { media: 'media/one.png', mediaItems: [{src:'media/one.png', source:'https://example.com/one'}, {src:'media/two.svg', source:'https://example.com/two'}] };
  const rendered = vm.runInContext('mediaPanel(item, true)', context);
  assert.match(rendered, /media\/one.png/);
  assert.match(rendered, /media\/two.svg/);
  assert.match(rendered, /href="https:\/\/example.com\/two"/);
});
