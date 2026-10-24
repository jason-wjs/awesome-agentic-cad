import {build} from 'esbuild';
await build({entryPoints:['scene.js'],bundle:true,outfile:'assets/scene.bundle.js',format:'iife',minify:true,legalComments:'external'});
console.log('Bundled local Three.js scene; no render-time external requests.');
