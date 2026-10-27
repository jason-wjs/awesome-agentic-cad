import {build} from 'esbuild';
await build({entryPoints:['timeline.js'],bundle:true,outfile:'assets/timeline.bundle.js',format:'iife',minify:true,legalComments:'external'});
console.log('Bundled the local composition timeline.');
