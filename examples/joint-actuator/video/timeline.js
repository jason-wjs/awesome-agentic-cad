import { gsap } from 'gsap';
const timeline = gsap.timeline({paused:true});
timeline.set('#phase',{textContent:'Section view'},0);
timeline.set('#phase',{textContent:'Assembly'},3);
timeline.set('#phase',{textContent:'Exploded view'},4.2);
timeline.set('#phase',{textContent:'Bore revision'},9);
timeline.fromTo('#progress',{scaleX:0},{scaleX:1,duration:12,ease:'none'},0);
window.jointTimeline=timeline;
