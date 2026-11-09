import type {Metadata} from 'next';
import {JetBrains_Mono,Nanum_Gothic_Coding,Orbitron} from 'next/font/google';
import 'maplibre-gl/dist/maplibre-gl.css';
import './globals.css';
import WorkflowWorkspace from '@/components/WorkflowWorkspace';
const display=Orbitron({subsets:['latin'],variable:'--ff-display',display:'swap'});
const mono=JetBrains_Mono({subsets:['latin'],variable:'--ff-mono',display:'swap'});
const monoKo=Nanum_Gothic_Coding({weight:['400','700'],subsets:['latin'],variable:'--ff-mono-ko',display:'swap',preload:false});
export const metadata:Metadata={title:'Satellite Insight AI | 위성영상 탐색',description:'실제 STAC 메타데이터에 근거한 위성영상 탐색과 예비 적합성 평가'};
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="ko" className={`${display.variable} ${mono.variable} ${monoKo.variable}`}><body><WorkflowWorkspace/>{children}</body></html>;}
