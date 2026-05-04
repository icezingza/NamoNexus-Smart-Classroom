# NamoNexus Frontend Aesthetics & UX Guide

This document defines the visual language and user experience standards for the NamoNexus interface.

## 1. Visual Philosophy
- **Aesthetic**: Premium Dark Mode, Cyber-Zen, Glassmorphism.
- **Experience**: The user should be "wowed" at first glance. Use vibrant colors, sleek dark modes, and dynamic animations.
- **Tone**: Sophisticated, professional, yet Gen-Z forward.

## 2. Color Palette (Sovereign Palette)
- **Primary**: Cyan (#06b6d4) - Represents wisdom and clarity.
- **Secondary**: Indigo (#4f46e5) - Represents stability and core logic.
- **Accents**: 
    - Rose (#f43f5e) - For errors and alerts.
    - Emerald (#10b981) - For success and active connections.
- **Background**: Slate-950/Slate-900 for a deep, premium dark feel.

## 3. UI Components & Patterns
- **Glassmorphism**: Use `backdrop-blur-md` and semi-transparent backgrounds (`bg-slate-900/40`) with thin borders (`border-white/10`).
- **Glows**: Subtle box-shadow glows for active elements (e.g., `glow-cyan`, `glow-indigo`).
- **Typography**: Modern sans-serif (Inter/Roboto/Outfit). Bold, uppercase tracking for labels and headers.
- **Layout**: Spacious, responsive, and tablet-optimized for classroom use.

## 4. Animations (Framer Motion)
- **Entry**: Smooth fade-in and slide-up for modals and panels.
- **Interaction**: Scale effects (95-97%) on button clicks.
- **Micro-animations**: Subtle pulses for AI status indicators and loading states.

## 5. Technical Implementation
- **CSS**: Tailwind CSS v4.
- **Icons**: Lucide React.
- **Components**: Focused, reusable, and strictly typed. No ad-hoc utility styles outside the design system tokens.

## 6. Prohibited Elements
- No generic browser colors (plain red, blue).
- No placeholder images (use premium assets or AI-generated visuals).
- No standard browser scrollbars (use custom thin slate scrollbars).
