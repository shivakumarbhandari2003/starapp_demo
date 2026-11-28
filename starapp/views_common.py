# -*- coding: utf-8 -*-
"""
STARAPP SHARED VIEW COMPONENTS
Reusable UI templates for liquid-glass containers, marksheets, timelines, and navigation.
"""

import html
import re
from typing import List, Dict, Any, Optional
from starapp.models import AssessmentMarksheet, BadgeTimeline, Badge, Notification, User, LearningMaterial


# ==============================================================================
# PROFESSIONAL VECTOR SVG ICON SYSTEM (Zero external font dependencies)
# ==============================================================================

ICON_SVGS = {
    "calendar": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    "clock": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
    "book": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>',
    "code": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>',
    "terminal": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>',
    "award": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "scale": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>',
    "clipboard": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>',
    "rocket": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path></svg>',
    "revoke": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path></svg>',
    "undo": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="9 14 4 9 9 4"></polyline><path d="M20 20v-7a4 4 0 0 0-4-4H4"></path></svg>',
    "lock": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>',
    "unlock": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>',
    "search": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
    "eye": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>',
    "edit": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>',
    "check": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    "check_circle": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    "plus": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
    "layers": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>',
    "globe": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
    "target": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>',
    "analytics": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    "map": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon><line x1="8" y1="2" x2="8" y2="18"></line><line x1="16" y1="6" x2="16" y2="22"></line></svg>',
    "user": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>',
    "users": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    "file_text": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>',
    "video": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>',
    "shield": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>',
    "bell": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>',
    "arrow_right": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>',
    "medal_1": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#D4AF37" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="6" fill="#FFD700" fill-opacity="0.25"></circle><path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8z" fill="#FFD700"></path><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "medal_2": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#8A9BA8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="6" fill="#C0C0C0" fill-opacity="0.25"></circle><path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8z" fill="#C0C0C0"></path><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "medal_3": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="#A97142" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="8" r="6" fill="#CD7F32" fill-opacity="0.25"></circle><path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.3-4.9-2.6-4.9 2.6.9-5.3-4-3.9 5.5-.8z" fill="#CD7F32"></path><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>',
    "star": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "flag": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>',
    "flash": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    "filter": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>',
    "external_link": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
    "alert_triangle": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    "github": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>',
    "download": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
    "copy": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>',
    "dollar": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    "compass": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>',
    "mail": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>',
    "eye_off": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>',
    "chevron_left": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="15 18 9 12 15 6"></polyline></svg>',
    "chevron_right": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="9 18 15 12 9 6"></polyline></svg>',
    "folder": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>',
    "wrench": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>',
    "send": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>',
    "refresh": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>',
    "x": '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;{st}"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
}

def get_icon(name: str, size: int = 15, style: str = "") -> str:
    """Returns a clean professional vector SVG icon."""
    template = ICON_SVGS.get(name)
    if not template:
        template = ICON_SVGS.get("award")
    return template.format(s=size, st=style)


def format_hms(total_seconds: int) -> str:
    """86399 -> '23:59:59' (the 24-hour countdown format)."""
    total_seconds = max(0, int(total_seconds))
    h, rem = divmod(total_seconds, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


IST_OFFSET = (5, 30)          # every timestamp shown to a user is Indian Standard Time (UTC+5:30); storage stays UTC


def to_ist(iso_value: Any) -> Any:
    """Parse a stored timestamp (UTC ISO, 'Z' or naive = UTC) into an aware datetime in IST, or None when empty / malformed."""
    import datetime as _dt
    try:
        dt = _dt.datetime.fromisoformat(str(iso_value or "").replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.astimezone(_dt.timezone(_dt.timedelta(hours=IST_OFFSET[0], minutes=IST_OFFSET[1])))


def format_ist(iso_value: Any, *, year: bool = True) -> str:
    """'2026-11-27T14:05:09+00:00' -> '27 Nov 2026, 19:35 IST' (year=False: '27 Nov, 19:35 IST'; '' when empty / malformed)."""
    dt = to_ist(iso_value)
    return dt.strftime("%d %b %Y, %H:%M IST" if year else "%d %b, %H:%M IST") if dt else ""


def ist_plain(iso_value: Any, seconds: bool = False) -> str:
    """'2026-11-27T14:05:09+00:00' -> '2026-11-27 19:35' (or ':09' with seconds) in IST, for tables whose header says IST; falls back to the raw text."""
    dt = to_ist(iso_value)
    if dt is None:
        return str(iso_value or "")[:19 if seconds else 16].replace("T", " ")
    return dt.strftime("%Y-%m-%d %H:%M:%S" if seconds else "%Y-%m-%d %H:%M")


def format_utc_stamp(iso_value: Any) -> str:
    """Kept for existing callers: '27 Nov, 19:35 IST' (the name is historical - nothing is shown in UTC any more)."""
    return format_ist(iso_value, year=False)


def render_countdown(
    seconds_left: int,
    prefix: str = "",
    suffix: str = "left",
    title: str = "",
    sync_action: str = "sync_mapping_requests",
    large: bool = False,
) -> str:
    """
    One live countdown chip for every deadline (24 h mapping request, 48 h badge review). The server renders the seconds
    left (no clock-skew); js/bridge.js ticks every `.rq-timer` once a second and, when one reaches zero, dispatches its
    `data-sync` action so the server applies the expiry and re-renders.
    """
    seconds_left = max(0, int(seconds_left))
    urgent = " is-urgent" if seconds_left < 3600 else ""
    big = " is-lg" if large else ""
    lead = f'<span class="rq-timer-lbl">{escape(prefix)}</span>' if prefix else ""
    tail = f'<span class="rq-timer-lbl">{escape(suffix)}</span>' if suffix else ""
    return (
        f'<span class="rq-timer{urgent}{big}" data-remaining="{seconds_left}" data-sync="{escape(sync_action)}" title="{escape(title)}">'
        f'{get_icon("clock", 14 if large else 13)}{lead}<span class="rq-timer-text">{format_hms(seconds_left)}</span>{tail}</span>'
    )


def render_request_timer(req: Dict[str, Any], prefix: str = "") -> str:
    """
    Live 24-hour countdown for a PENDING mapping request, shown to the Guardian and to the reviewer.
    Returns '' for answered requests or requests that carry no deadline.
    """
    from starapp.storage import mapping_request_seconds_left
    left = mapping_request_seconds_left(req)
    if left is None:
        return ""
    return render_countdown(left, prefix, "left", "Time left to respond. After 24 hours without an answer the request counts as not accepted.")


def render_badge_review_timer(due_iso: Any, large: bool = True) -> str:
    """Live countdown of a badge's 48-hour review window ('' for legacy date-only deadlines)."""
    from starapp.storage import badge_review_seconds_left
    left = badge_review_seconds_left(due_iso)
    if left is None:
        return ""
    return render_countdown(
        left, "", "left to review",
        "Time left to review and edit this badge. When it reaches zero the review closes and the badge stays exactly as it is.",
        sync_action="sync_badge_reviews", large=large,
    )


def render_project_window_timer(published_at: Any, large: bool = False, suffix: str = "left to send projects") -> str:
    """
    Live countdown of the reviewer's 72-hour window (from the moment the badge was published) to create the project and send it
    to every mapped cosmonaut. When it runs out the chip reads "Project window ended". '' when the badge has no publish time.
    """
    from starapp.storage import project_window_seconds_left
    left = project_window_seconds_left(published_at)
    if left is None:
        return ""
    if left == 0:
        return f'<span class="rq-timer is-expired{" is-lg" if large else ""}">{get_icon("clock", 13)}<span class="rq-timer-lbl">Project window ended</span></span>'
    return render_countdown(
        left, "", suffix,
        "From the moment this badge was published the reviewer has 72 hours to create the project and send it to every mapped cosmonaut.",
        sync_action="sync_badge_reviews", large=large,
    )


def format_short_date(value: Any) -> str:
    """'2026-11-18' / '2026-11-18T10:00:00+00:00' -> '18 Nov 2026' ('' when empty / malformed)."""
    import datetime as _dt
    try:
        return _dt.date.fromisoformat(str(value or "")[:10]).strftime("%d %b %Y")
    except Exception:
        return ""


def escape(text: Any) -> str:
    return html.escape(str(text or ""))


def render_taxonomy_hierarchy_tree(power: str, capability: str, skill: str, compact: bool = False) -> str:
    """Renders a unified clickable Skill pill that unfolds in-place into a connected Power -> Capability -> Skill lineage tree."""
    p_val = escape(power or "Tech")
    c_val = escape(capability or "Data & Machine")
    s_val = escape(skill or "Foundations")
    compact_cls = " is-compact" if compact else ""
    layers_svg = (
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 2L2 7l10 5 10-5-10-5z"/>'
        '<path d="M2 17l10 5 10-5"/>'
        '<path d="M2 12l10 5 10-5"/></svg>'
    )
    chev_svg = (
        '<svg class="lg-hier-chevron" width="11" height="11" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<polyline points="9 18 15 12 9 6"/></svg>'
    )
    return f"""
    <details class="lg-hier-disclosure{compact_cls}" onclick="event.stopPropagation();">
        <summary class="lg-hier-summary" title="Click to toggle connected Power &rarr; Capability &rarr; Skill lineage">
            <span class="lg-hier-summary-closed">
                <span class="lg-hier-skill-dot" aria-hidden="true"></span>
                <span class="lg-hier-k">Skill :</span>
                <span class="lg-hier-v">{s_val}</span>
            </span>
            <span class="lg-hier-summary-open">
                <span class="lg-hier-path-ico" aria-hidden="true">{layers_svg}</span>
                <span class="lg-hier-open-label">Taxonomy Lineage</span>
            </span>
            <span class="lg-hier-chev-pill" aria-hidden="true">{chev_svg}</span>
        </summary>
        <div class="lg-hier-tree{compact_cls}">
            <div class="lg-hier-row is-power">
                <span class="lg-hier-dot" aria-hidden="true"></span>
                <span class="lg-hier-k">Power :</span>
                <span class="lg-hier-v">{p_val}</span>
            </div>
            <div class="lg-hier-row is-cap">
                <span class="lg-hier-branch is-cap-node" aria-hidden="true"></span>
                <span class="lg-hier-k">Capability :</span>
                <span class="lg-hier-v">{c_val}</span>
            </div>
            <div class="lg-hier-row is-skill">
                <span class="lg-hier-branch is-skill-node" aria-hidden="true"></span>
                <span class="lg-hier-k">Skill :</span>
                <span class="lg-hier-v">{s_val}</span>
            </div>
        </div>
    </details>
    """

def render_liquid_card(
    content: str,
    title: str = "",
    subtitle: str = "",
    actions_html: str = "",
    dark: bool = False,
    extra_class: str = "",
    card_id: str = ""
) -> str:
    """Standard reusable Liquid-Glass container matching code.txt specification."""
    dark_class = "dark" if dark else ""
    id_attr = f'id="{escape(card_id)}"' if card_id else ""
    header_html = ""
    if title or actions_html:
        header_html = f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; border-bottom:1px solid var(--icy-steel-30); padding-bottom:12px;">
            <div>
                {f'<h3 style="font-size:1.1rem; font-weight:700; color:inherit; margin:0;">{escape(title)}</h3>' if title else ''}
                {f'<p style="font-size:0.8rem; color:inherit; opacity:0.75; margin-top:2px;">{escape(subtitle)}</p>' if subtitle else ''}
            </div>
            {f'<div>{actions_html}</div>' if actions_html else ''}
        </div>
        """
    return f"""
    <div class="liquid-glass-card {dark_class} {escape(extra_class)}" {id_attr}>
        <div class="card-content">
            {header_html}
            {content}
        </div>
    </div>
    """

def render_liquid_button(
    text: str,
    action: str,
    payload_json: str = "{}",
    extra_class: str = "",
    icon_svg: str = ""
) -> str:
    """Button implementing the liquid styling from code.txt."""
    onclick_attr = f"window.StarAppBridge.dispatchAction('{escape(action)}', '{escape(payload_json)}')"
    return f"""
    <button type="button" class="btn-liquid {escape(extra_class)}" onclick="{onclick_attr}">
        {icon_svg}
        <span>{escape(text)}</span>
    </button>
    """

def render_metal_button(
    text: str,
    action: str,
    payload_json: str = "{}",
    variant: str = "primary",
    icon_svg: str = ""
) -> str:
    """3D tactile button matching MetalButton from code.txt."""
    onclick_attr = f"window.StarAppBridge.dispatchAction('{escape(action)}', '{escape(payload_json)}')"
    return f"""
    <div class="btn-metal-wrapper">
        <div class="btn-metal-inner"></div>
        <button type="button" class="btn-metal" onclick="{onclick_attr}">
            {icon_svg}
            <span>{escape(text)}</span>
        </button>
    </div>
    """

# Countdowns are rendered with the seconds left, so two renders of an unchanged page differ every second. That must never cause a repaint:
# the browser (bridge.js `_stableHtml`) and the server (`stable_html_signature`, used to answer a live-sync poll with "unchanged") compare
# HTML with those values blanked out. The timers tick on their own in the browser.
_VOLATILE_TIMER_RE = re.compile(r'data-remaining="\d+"|(?<=<span class="rq-timer-text">)[\d:]+')


def stable_html_signature(html: str) -> str:
    """HTML with the ticking countdown values removed (identical for two renders of an unchanged page)."""
    return _VOLATILE_TIMER_RE.sub("", html or "")


def render_back_button(
    target_action: str = "go_back",
    payload_json: str = "{}",
    label: str = "Back",
    extra_style: str = ""
) -> str:
    """Universal Back lives in the top-right header bar; omit duplicate inline go_back buttons."""
    if target_action == "go_back":
        return ""
    onclick_attr = f"window.StarAppBridge.dispatchAction('{escape(target_action)}', '{escape(payload_json)}')"
    return f"""
    <button type="button" class="btn-secondary btn-sm" onclick="{onclick_attr}"
            style="font-size:0.78125rem; font-weight:700; display:inline-flex; align-items:center; gap:6px; padding:6px 14px; border-radius:var(--radius-sm); {extra_style}"
            title="Navigate back">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
        <span>{escape(label)}</span>
    </button>
    """

def render_status_pill(status: str) -> str:
    status_lower = (status or "").lower().replace(" ", "_")
    cls_map = {
        "approved": "status-approved",
        "completed": "status-completed",
        "active": "status-active",
        "pending": "status-pending",
        "awaiting_review": "status-awaiting-review",
        "reviewer_assessed": "status-warning",
        "resubmission_requested": "status-resubmit",
        "rejected": "status-rejected",
        "locked": "status-locked"
    }
    css_class = cls_map.get(status_lower, "status-pending")
    label = status.replace("_", " ").title()
    return f'<span class="status-pill {css_class}">{escape(label)}</span>'

# The reviewer's recommendation to the Guardian on a submission: Give Badge / Re-attempt / Reject. Stored on the reviewer's marksheet
# (`decision` = recommend_approve / recommend_resubmit / recommend_reject, so no "approve" check ever mistakes it for an award).
REVIEWER_RECOMMENDATIONS = {
    "approve": {"label": "Give Badge", "icon": "award", "tone": "green", "desc": "Recommend the Guardian awards the badge."},
    "resubmission_requested": {"label": "Re-attempt", "icon": "refresh", "tone": "amber", "desc": "Recommend a new attempt; this one stays on record."},
    "reject": {"label": "Reject", "icon": "x", "tone": "red", "desc": "Recommend rejecting this attempt."},
}
_REC_ALIASES = {
    "approve": "approve", "approved": "approve", "recommend_approve": "approve", "award": "approve", "earn": "approve", "give_badge": "approve",
    "resubmission_requested": "resubmission_requested", "resubmit": "resubmission_requested", "recommend_resubmit": "resubmission_requested",
    "changes_requested": "resubmission_requested", "request_revision": "resubmission_requested", "reattempt": "resubmission_requested", "re_attempt": "resubmission_requested",
    "reject": "reject", "rejected": "reject", "recommend_reject": "reject",
}


def normalize_decision(value: Any) -> str:
    """Any spelling of a decision -> 'approve' | 'resubmission_requested' | 'reject' ('' when not a decision)."""
    return _REC_ALIASES.get(str(value or "").strip().lower(), "")


def reviewer_recommendation_key(asm: Any) -> str:
    """The recommendation recorded on a REVIEWER marksheet ('' for Guardian sheets, legacy 'reviewer_assessed', or none)."""
    if not asm or getattr(asm, "assessor_role", "") != "reviewer":
        return ""
    return normalize_decision(getattr(asm, "decision", ""))


def render_recommendation_chip(key: str, prefix: str = "Reviewer recommends") -> str:
    """Small icon chip: 'Reviewer recommends: Give Badge' (empty string when there is no recommendation)."""
    info = REVIEWER_RECOMMENDATIONS.get(key)
    if not info:
        return ""
    lead = f"{escape(prefix)}: " if prefix else ""
    return f'<span class="rec-chip is-{info["tone"]}">{get_icon(info["icon"], 13)}<span>{lead}<b>{info["label"]}</b></span></span>'


_MS_CRITERIA = (
    ("Business Understanding", "Problem formulation, compliance boundaries and business value.", "business_understanding"),
    ("Architecture / Report", "Modularity, system design rigour, diagrams and written documentation.", "architecture_report"),
    ("Technical Knowledge", "Code robustness, optimisation, edge-case coverage and efficiency.", "technical_knowledge"),
    ("Presentation", "Narrative clarity, structured delivery and verification packaging.", "presentation"),
    ("Question & Answering", "Defence of trade-offs, conceptual agility and domain comprehension.", "qa"),
)


def _ms_outcome(marksheet: AssessmentMarksheet) -> Dict[str, str]:
    """Tone, label and note for a marksheet: reviewer-only sheets are provisional until the Guardian decides."""
    decision = (getattr(marksheet, "decision", "") or "").lower()
    is_reviewer = getattr(marksheet, "assessor_role", "") == "reviewer" or decision == "reviewer_assessed"
    if is_reviewer:
        rec = reviewer_recommendation_key(marksheet)
        said = f" and recommends <b>{REVIEWER_RECOMMENDATIONS[rec]['label']}</b>" if rec else ""
        return {"tone": "blue", "label": "Awaiting Guardian", "icon": "clock",
                "note": f"Evaluated by your peer reviewer{said}. The Guardian gives the final decision.", "note_is_html": "1"}
    if decision in ("approve", "approved"):
        return {"tone": "green", "label": "Badge earned", "icon": "award", "note": "Approved by the Guardian - the badge is certified."}
    if decision in ("rejected", "reject"):
        return {"tone": "red", "label": "Rejected", "icon": "x", "note": "This attempt was rejected. Review the feedback and start a new attempt."}
    return {"tone": "red", "label": "Re-attempt", "icon": "refresh", "note": "Below the passing threshold or a new attempt was requested. Review the feedback and resubmit."}


def _ms_reviewer_name(marksheet: AssessmentMarksheet) -> str:
    """The real peer reviewer of this attempt (their own marksheet, else the mapped reviewer) - never the Guardian who signed it off."""
    from starapp.storage import store
    if getattr(marksheet, "assessor_role", "") == "reviewer":
        return str(marksheet.reviewer_name or "")
    try:
        for a in store.get_assessments_for_cosmonaut(marksheet.cosmonaut_id, marksheet.badge_id):
            if getattr(a, "assessor_role", "") == "reviewer" and a.attempt_number == marksheet.attempt_number and a.reviewer_name:
                return str(a.reviewer_name)
        rid = store.get_mapped_reviewer_id(marksheet.badge_id, marksheet.cosmonaut_id)
        u = store.get_user_by_id(rid) if rid else None
        if u:
            return u.name
    except Exception:
        pass
    return str(marksheet.reviewer_name or "")


def render_standard_marksheet(
    marksheet: AssessmentMarksheet,
    badge: Optional[Badge] = None,
    all_attempts: Optional[List[AssessmentMarksheet]] = None,
    tab_action: str = "view_marksheet",
) -> str:
    """
    The official 50-mark marksheet (glass): a hero with the badge, attempt, evaluator and the score ring; four result tiles (total,
    percentage, pass mark, result); the evaluation tabs (every attempt x reviewer / Guardian, via `tab_action`); the five criteria in ONE
    card (name + scope, meter, score with a one-word rating); strengths / growth areas and the evaluator's summary.
    """
    badge_title = badge.title if badge else "Project Assessment"
    badge_code = badge.code if badge else "STAR-RUBRIC"
    is_reviewer = getattr(marksheet, "assessor_role", "") == "reviewer"
    assessor_title = "Peer Reviewer" if is_reviewer else "Guardian"
    out = _ms_outcome(marksheet)
    pct_val = max(0.0, min(100.0, float(marksheet.percentage or 0.0)))
    thr = float(getattr(badge, "passing_percentage", 70.0) or 70.0) if badge else 70.0
    met = pct_val >= thr
    name = _ms_reviewer_name(marksheet)
    rows = []
    for idx, (cname, scope, attr) in enumerate(_MS_CRITERIA, 1):
        score = float(getattr(marksheet, attr, 0.0) or 0.0)
        pct = max(0, min(100, int(round(score / 10.0 * 100))))
        level = "high" if score >= 8 else ("mid" if score >= 6 else "low")
        rows.append(f"""
            <div class="ms-crit">
                <span class="ms-crit-num">{idx}</span>
                <div class="ms-crit-name">{escape(cname)}</div>
                <div class="ms-meter"><span class="ms-meter-fill is-{level}" style="width:{pct}%;"></span></div>
                <div class="ms-crit-score"><b>{score:.1f}</b><small>/ 10</small></div>
            </div>""")

    strengths = escape(marksheet.strength_areas or "No specific strengths highlighted.")
    growth = escape(marksheet.improvement_areas or "No critical weaknesses noted.")
    synthesis = escape(marksheet.overall_feedback or "No feedback recorded.")

    return f"""
    <div class="marksheet-view ms-sheet">
        <div class="ms-hero">
            <div class="ms-hero-main">
                <div class="ms-title" role="heading" aria-level="2">{escape(badge_title)}</div>
            </div>
        </div>

        <div class="ms-body">
            <div class="ms-stats">
                <div class="ms-stat"><div class="ms-stat-lbl">Reviewer</div><div class="ms-stat-val is-text">{escape(name)}</div></div>
                <div class="ms-stat"><div class="ms-stat-lbl">Attempt</div><div class="ms-stat-val">#{marksheet.attempt_number}</div></div>
                <div class="ms-stat"><div class="ms-stat-lbl">Total score</div><div class="ms-stat-val">{marksheet.total_marks:.1f}<small> / 50</small></div></div>
                <div class="ms-stat"><div class="ms-stat-lbl">Percentage</div><div class="ms-stat-val">{marksheet.percentage:.1f}%</div></div>
                <div class="ms-stat"><div class="ms-stat-lbl">Pass mark</div><div class="ms-stat-val">{thr:.0f}%</div></div>
            </div>

            <div class="ms-card">
                <div class="ms-card-head"><span class="ms-card-title">{get_icon("clipboard", 16)}<span>Rubric breakdown</span></span><span class="ms-card-hint">5 criteria &middot; 10 marks each</span></div>
                {"".join(rows)}
                <div class="ms-total"><span>Total</span><span class="ms-total-val">{marksheet.total_marks:.1f} <small>/ 50.0</small></span></div>
            </div>

            <div class="ms-feedback">
                <div class="ms-fb-card is-good"><div class="ms-fb-lbl">{get_icon("check_circle", 15)}<span>Strengths &amp; distinctions</span></div><p>{strengths}</p></div>
                <div class="ms-fb-card is-grow"><div class="ms-fb-lbl">{get_icon("flag", 15)}<span>Areas for growth</span></div><p>{growth}</p></div>
            </div>
        </div>
    </div>
    """


def render_9point_timeline(timeline: BadgeTimeline, badge: Optional[Badge] = None) -> str:
    """Renders the comprehensive 9-point milestone timeline for a badge."""
    badge_title = badge.title if badge else "Training Milestone"
    nodes = [
        {"num": 1, "label": "Badge Assignment", "date": timeline.assignment_date, "desc": "Assigned to Cosmonaut dossier"},
        {"num": 2, "label": "Roadmap Publication", "date": timeline.publication_date, "desc": "Published on learning roadmap"},
        {"num": 3, "label": "Learning Phase Commences", "date": timeline.learning_start_date, "desc": "Study materials & theory modules"},
        {"num": 4, "label": "Learning Phase Concludes", "date": timeline.learning_end_date, "desc": "Curriculum completion cutoff"},
        {"num": 5, "label": "Project Implementation Begins", "date": timeline.project_start_date, "desc": "Hands-on build & engineering phase"},
        {"num": 6, "label": "Project Implementation Ends", "date": timeline.project_end_date, "desc": "Final test runs & artifact preparation"},
        {"num": 7, "label": "Official Submission Deadline", "date": timeline.submission_deadline, "desc": "Hard deadline for deliverable intake"},
        {"num": 8, "label": "Guardian Review & Q&A Defense", "date": timeline.review_date, "desc": "Standard 50-mark marksheet evaluation"},
        {"num": 9, "label": "Badge Award Date", "date": timeline.actual_award_date or timeline.expected_award_date, "desc": "Credential credentialing on blockchain/ledger"}
    ]

    items_html = []
    for node in nodes:
        is_past = bool(node["date"] and node["date"] <= "2026-11-07")  # Current system demo date
        node_cls = "completed" if is_past else "active"
        items_html.append(f"""
        <div class="timeline-node {node_cls}">
            <div>
                <div class="timeline-label">{node["num"]}. {escape(node["label"])}</div>
                <div style="font-size:0.71875rem; color:var(--frost-navy-50);">{escape(node["desc"])}</div>
            </div>
            <div class="timeline-date">{escape(node["date"] or "TBD")}</div>
        </div>
        """)

    return f"""
    <div>
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
            <h4 style="font-size:1.1rem; font-weight:700; color:var(--frost-navy); margin:0;">{escape(badge_title)} &mdash; Lifecycle Timeline</h4>
            {render_status_pill(timeline.status)}
        </div>
        <div class="timeline-flow">
            {"".join(items_html)}
        </div>
    </div>
    """

def render_cycle_context_bar(
    cycles: List[Any],
    selected_cycle: Optional[Any],
    is_guardian: bool = False,
    current_view: str = ""
) -> str:
    """Renders a compact Topbar Cycle Switcher showing the 6-month cycle window, status, and switcher."""
    if not selected_cycle:
        return ""

    c_id = getattr(selected_cycle, "id", "")
    c_name = getattr(selected_cycle, "name", c_id)
    c_start = getattr(selected_cycle, "start_date", "")
    c_end = getattr(selected_cycle, "end_date", "")
    c_status = (getattr(selected_cycle, "status", "active") or "active").lower()

    if c_status == "closed":
        status_badge = '<span style="background:rgba(100,116,139,0.16); color:#334155; border:1px solid #94A3B8; font-size:0.65625rem; font-weight:800; padding:2px 9px; border-radius:999px; letter-spacing:0.4px;">CLOSED &bull; READ-ONLY ARCHIVE</span>'
    elif c_status == "evaluating":
        status_badge = '<span style="background:rgba(245,158,11,0.14); color:#B45309; border:1px solid #FBBF24; font-size:0.65625rem; font-weight:800; padding:2px 9px; border-radius:999px; letter-spacing:0.4px;">EVALUATING CYCLE</span>'
    else:
        status_badge = '<span style="background:rgba(16,185,129,0.14); color:#047857; border:1px solid rgba(16,185,129,0.35); font-size:0.65625rem; font-weight:800; padding:2px 9px; border-radius:999px; letter-spacing:0.4px;">ACTIVE 6-MONTH CYCLE</span>'

    opts = []
    for cyc in cycles:
        sel = " selected" if getattr(cyc, "id", "") == c_id else ""
        st_lbl = (getattr(cyc, "status", "active") or "active").upper()
        opts.append(
            f'<option value="{escape(cyc.id)}"{sel}>{escape(cyc.name)} ({escape(cyc.start_date)} &rarr; {escape(cyc.end_date)}) [{st_lbl}]</option>'
        )

    nav_action = "nav_guardian" if is_guardian else "nav_cosmonaut"
    cycles_view = "g_cycles" if is_guardian else "c_choose_cycle"
    cycles_btn_label = "Cycles & Performance" if is_guardian else "Cycles & Appraisals"

    guardian_create_btn = ""
    if is_guardian:
        guardian_create_btn = """
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('open_create_cycle_modal', '{}')"
                style="font-size:0.71875rem; font-weight:800; padding:5px 11px; white-space:nowrap;">
            + New 6-Month Cycle
        </button>
        """

    cycles_nav_btn = ""
    if current_view != cycles_view:
        cycles_nav_btn = f"""
        <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('{nav_action}', '{cycles_view}')"
                style="font-size:0.71875rem; font-weight:700; padding:5px 11px; white-space:nowrap; color:var(--deep-frozen-midnight);">
            {escape(cycles_btn_label)} &rarr;
        </button>
        """

    return f"""
    <div id="starapp-cycle-topbar" style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-bottom:18px; padding:10px 16px; border-radius:var(--radius-md); background:rgba(244, 250, 255, 0.87); border:1px solid var(--icy-steel-50); box-shadow:0 3px 12px rgba(7,22,41,0.04);">
        <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <span style="display:inline-flex; align-items:center; gap:6px; font-size:0.75rem; font-weight:800; color:var(--deep-frozen-midnight);">
                {get_icon("calendar", 14)}
                <span>{escape(c_name)}</span>
            </span>
            <span style="font-family:var(--font-family-mono); font-size:0.71875rem; font-weight:700; color:var(--frost-navy-50);">
                {escape(c_start)} &rarr; {escape(c_end)}
            </span>
            {status_badge}
        </div>
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <label for="topbar-cycle-select" style="font-size:0.6875rem; font-weight:800; color:var(--frost-navy-50); text-transform:uppercase; letter-spacing:0.4px;">Cycle:</label>
            <select id="topbar-cycle-select" class="liquid-glass-control liquid-glass-select"
                    style="font-size:0.75rem; font-weight:700; padding:4px 10px; min-width:250px; height:32px;"
                    onchange="window.StarAppBridge.dispatchAction('select_cycle', this.value)">
                {"".join(opts)}
            </select>
            {cycles_nav_btn}
            {guardian_create_btn}
        </div>
    </div>
    """


def render_sidebar_cycle_pill(
    selected_cycle: Optional[Any],
    nav_action: str,
    choose_cycle_view: str
) -> str:
    """Renders a compact Global Cycle Filter badge inside the portal sidebar (no repeated per-page topbar)."""
    if not selected_cycle:
        return ""

    c_code = getattr(selected_cycle, "code", None) or getattr(selected_cycle, "id", "CYCLE")
    c_name = getattr(selected_cycle, "name", "Cycle")
    c_start = getattr(selected_cycle, "start_date", "")
    c_end = getattr(selected_cycle, "end_date", "")
    c_status = (getattr(selected_cycle, "status", "active") or "active").lower()

    if c_status == "closed":
        dot_color = "#94A3B8"
        st_lbl = "CLOSED"
    elif c_status == "evaluating":
        dot_color = "#F59E0B"
        st_lbl = "EVAL"
    else:
        dot_color = "#10B981"
        st_lbl = "ACTIVE"

    # The collapsed rail is 72px wide: show "C1" (not a clipped "C1-202"); the full code shows when it expands.
    short_code = escape(str(c_code).split("-")[0][:4])
    return f"""
    <div id="starapp-sidebar-cycle-pill" class="sidebar-band-switcher">
        <div class="band-switcher-mini" title="Switch Cycle Filter: {escape(c_name)} ({escape(c_start)} to {escape(c_end)})">
            <button type="button"
                    onclick="window.StarAppBridge.dispatchAction('{escape(nav_action)}', '{escape(choose_cycle_view)}')"
                    style="font-family:var(--font-family-mono); font-size:0.625rem; font-weight:800; background:rgba(255,255,255,0.92); border:1.5px solid {dot_color}; color:var(--frost-navy); padding:3px 7px; border-radius:999px; cursor:pointer;"
                    aria-label="Switch Cycle Filter">{short_code[:6]}</button>
        </div>
        <div class="band-switcher-content">
            <button type="button"
                    onclick="window.StarAppBridge.dispatchAction('{escape(nav_action)}', '{escape(choose_cycle_view)}')"
                    title="Switch Cycle Filter: {escape(c_name)}"
                    style="width:100%; display:flex; align-items:center; justify-content:space-between; gap:8px; padding:4px 10px; border-radius:999px; background:rgba(255,255,255,0.92); border:1px solid rgba(157,183,213,0.55); color:var(--frost-navy); font-size:0.71875rem; font-weight:800; cursor:pointer;">
                <span style="overflow:hidden; text-overflow:ellipsis;">{escape(c_code)}</span>
                <span style="font-family:var(--font-family-mono); font-size:0.625rem; font-weight:800; background:{dot_color}; color:#fff; padding:1px 7px; border-radius:999px; flex-shrink:0;">{st_lbl}</span>
            </button>
        </div>
    </div>
    """


def render_topbar(
    current_user: User,
    page_title: str,
    unread_notifs_count: int = 0
) -> str:
    """Renders the consistent top bar with role indicator, notification bell, demo reset, and logout."""
    bell_badge = f'<span class="notif-badge">{unread_notifs_count}</span>' if unread_notifs_count > 0 else ""
    return f"""
    <header class="app-topbar">
        <div class="topbar-left" style="display:flex; align-items:center; gap:10px;">
            <button type="button" class="topbar-sidebar-toggle-btn" onclick="window.StarAppBridge.toggleSidebar()" title="Toggle Sidebar Navigation">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
            </button>
            <h1 class="topbar-page-title">{escape(page_title)}</h1>
        </div>
        <div class="topbar-right">
            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('reset_demo_data', '{{}}')" title="Restore initial clean dataset">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
                Demo Reset
            </button>

            <button type="button" class="notif-btn" onclick="window.StarAppBridge.dispatchAction('toggle_notifications_modal', '{{}}')" title="View Notifications">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
                {bell_badge}
            </button>

            <div style="display:flex; align-items:center; gap:10px; padding-left:8px; border-left:1px solid var(--icy-steel-30);">
                <div class="user-avatar" style="width:34px; height:34px; font-size:0.75rem;">{escape(current_user.avatar)}</div>
                <div style="line-height:1.2;">
                    <div style="font-size:0.84375rem; font-weight:700; color:var(--frost-navy);">{escape(current_user.name)}</div>
                    <div style="font-size:0.71875rem; text-transform:uppercase; color:var(--deep-frozen-midnight); font-weight:700;">{escape(current_user.role)}</div>
                </div>
            </div>

            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" title="Switch User or Logout">
                Sign Out
            </button>

            <button type="button" class="btn-secondary btn-sm" onclick="window.StarAppBridge.dispatchAction('go_back', '{{}}')"
                    style="font-size:0.78125rem; font-weight:700; display:inline-flex; align-items:center; gap:5px; padding:6px 14px; border-radius:var(--radius-sm); color:var(--frost-navy);"
                    title="Go back to previous screen">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
                <span>Back</span>
            </button>
        </div>
    </header>
    """


# Views whose own page heading (first <h1>/<h2>) is shown in the Back-button row instead of inside the page.
# Hero-style pages (dashboards, profile, cycle cards, band picker, roadmaps) keep their designed headers.
TITLE_HOIST_VIEWS = frozenset({
    "g_badge_approval", "g_mapping", "g_reviews", "g_materials", "g_extensions", "g_announcements", "g_activity",
    "c_submission", "c_results", "c_materials", "c_announcements", "c_extensions", "c_activity",
    "c_requests", "c_badge_reviews", "g_mapping_badge_detail", "c_badge_review",
})

_PAGE_HEADING_RE = re.compile(r"<(h1|h2)\b([^>]*)>(.*?)</\1>", re.S | re.I)


def hoist_page_title(main_html: str, max_offset: int = 1600):
    """
    Finds the page's own heading (first <h1>/<h2> near the top) and returns (html, title_text).
    The heading stays in the DOM, visually hidden (`app-title-hoisted`), so the document keeps its heading
    structure for assistive tech; the visible copy is rendered in the Back-button row by `render_global_back_bar`.
    Returns the HTML unchanged and an empty title when there is no suitable heading.
    """
    m = _PAGE_HEADING_RE.search(main_html or "")
    if not m or m.start() > max_offset:
        return main_html, ""
    text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(3)))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return main_html, ""
    attrs = m.group(2)
    if 'class="' in attrs:
        attrs = attrs.replace('class="', 'class="app-title-hoisted ', 1)
    else:
        attrs = attrs + ' class="app-title-hoisted"'
    new_tag = f"<{m.group(1)}{attrs}>{m.group(3)}</{m.group(1)}>"
    return main_html[:m.start()] + new_tag + main_html[m.end():], text


def render_global_back_bar(title: str = "") -> str:
    """Universal top strip: the page title (when the view provides one) on the left, the Back button on the right."""
    title_html = (
        f'<div class="app-strip-title" aria-hidden="true" title="{html.escape(title, quote=True)}">{html.escape(title)}</div>'
        if title else ""
    )
    return f"""
    <div class="app-back-strip">
        {title_html}
        <div class="topbar-right">
            <button type="button" class="btn-secondary btn-sm app-global-back-btn"
                    onclick="window.StarAppBridge.dispatchAction('go_back', '{{}}')"
                    title="Go back to previous page">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
                <span>Back</span>
            </button>
        </div>
    </div>
    """


# ==============================================================================
# UNIFIED LEARNING & DEVELOPMENT MATERIALS WORKSPACE
# ==============================================================================

def extract_youtube_video_id(url_or_data: str) -> str:
    """Extract standard 11-char YouTube ID from any url shape."""
    if not url_or_data:
        return "9ZGFF_bYenc"
    s = url_or_data.strip()
    if "watch?v=" in s:
        vid = s.split("watch?v=")[1].split("&")[0].split("#")[0]
        if vid:
            return vid
    if "youtu.be/" in s:
        vid = s.split("youtu.be/")[1].split("?")[0].split("#")[0]
        if vid:
            return vid
    if "/embed/" in s:
        vid = s.split("/embed/")[1].split("?")[0].split("#")[0]
        if vid:
            return vid
    if "/shorts/" in s:
        vid = s.split("/shorts/")[1].split("?")[0].split("#")[0]
        if vid:
            return vid
    return s if (len(s) == 11 and " " not in s) else "9ZGFF_bYenc"


def render_learning_materials_view(
    materials: List[LearningMaterial],
    badges: List[Badge],
    badges_map: Dict[str, Badge],
    selected_badge_filter: str = "all",
    selected_type_filter: str = "all",
    is_guardian: bool = False
) -> str:
    """
    Renders the unified, responsive learning and development resource hub for both Guardian and Cosmonaut.
    Guardian gains Add / Edit / Delete management controls; Cosmonaut has clean read/view access.
    """
    # 1. Determine scoped badges
    if selected_badge_filter == "all":
        target_badges = badges
    else:
        target_badges = [b for b in badges if b.id == selected_badge_filter]
        if not target_badges and selected_badge_filter in badges_map:
            target_badges = [badges_map[selected_badge_filter]]

    # Counts in current scope
    scope_materials = [m for m in materials if any(b.id == m.badge_id for b in target_badges)]
    count_all = len(scope_materials)
    count_pdf = sum(1 for m in scope_materials if m.material_type == "pdf")
    count_yt = sum(1 for m in scope_materials if m.material_type == "youtube")

    # Badge filter dropdown
    badge_opts = [f'<option value="all"{" selected" if selected_badge_filter == "all" else ""}>All Milestone Badges</option>']
    for b in badges:
        sel = " selected" if b.id == selected_badge_filter else ""
        badge_opts.append(f'<option value="{b.id}"{sel}>{escape(b.code)}: {escape(b.title)}</option>')

    # Type button styling helper
    def get_btn_style(is_active: bool) -> str:
        if is_active:
            return "background:var(--deep-frozen-midnight); color:var(--snow-white); font-weight:800; border-radius:var(--radius-sm); padding:7px 16px; font-size:0.78125rem; border:none; cursor:pointer; box-shadow:0 2px 8px rgba(23,52,92,0.3); display:inline-flex; align-items:center; gap:6px;"
        return "background:transparent; color:var(--deep-frozen-midnight); font-weight:700; border-radius:var(--radius-sm); padding:7px 16px; font-size:0.78125rem; border:none; cursor:pointer; display:inline-flex; align-items:center; gap:6px; opacity:0.85;"

    btn_all_style = get_btn_style(selected_type_filter == "all")
    btn_pdf_style = get_btn_style(selected_type_filter == "pdf")
    btn_yt_style = get_btn_style(selected_type_filter == "youtube")

    # Header action (Guardian only)
    header_title = "Learning & Development Hub" if is_guardian else "Course Documents & Video Lectures"
    header_desc = "Upload course syllabi, technical PDF documentation, and embedded YouTube video lectures." if is_guardian else "Curated technical whitepapers, architectural specifications, and video masterclasses."
    header_action_html = ""
    if is_guardian:
        header_action_html = """
        <button type="button" class="btn-metal" style="display:inline-flex; align-items:center; gap:6px; font-weight:800; font-size:0.78125rem; padding:8px 16px;" onclick="window.StarAppBridge.dispatchAction('open_add_material_modal', '{}')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            + Upload Learning Materials
        </button>
        """

    # 2. Render badge sections
    badge_sections = []
    for b in target_badges:
        b_mats = [m for m in materials if m.badge_id == b.id]
        if selected_type_filter == "pdf":
            b_mats = [m for m in b_mats if m.material_type == "pdf"]
        elif selected_type_filter == "youtube":
            b_mats = [m for m in b_mats if m.material_type == "youtube"]

        # Only skip if no materials and "all" filter is active
        if not b_mats and selected_badge_filter == "all":
            continue

        mat_cards = []
        for m in b_mats:
            if m.material_type == "pdf":
                type_pill = """
                <span style="background:rgba(23,52,92,0.08); color:var(--deep-frozen-midnight); padding:3px 8px; border-radius:var(--radius-xs); font-size:0.65625rem; font-weight:800; border:1px solid var(--icy-steel-50); display:inline-flex; align-items:center; gap:5px;">
                    <svg viewBox="0 0 24 24" style="width:12px; height:12px;" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    PDF DOCUMENT
                </span>
                """
                read_indicator = '<span style="font-size:0.6875rem; font-weight:700; color:var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:4px;">&bull; Clickable PDF</span>'
                pdf_src = m.url_or_data.replace(' ', '%20') if (m.url_or_data and not m.url_or_data.startswith('http') and not m.url_or_data.startswith('data:')) else (m.url_or_data or 'data/Chemistry%20Syllabus.pdf')
                media_viewer_html = f"""
                <div class="media-pdf-box" style="cursor:pointer; position:relative;" onclick="window.StarAppBridge.dispatchAction('view_material_preview', '{m.id}');" title="Click to open and read PDF in large window">
                    <object data="{escape(pdf_src)}" type="application/pdf" style="pointer-events:none; width:100%; height:100%;">
                        <iframe src="{escape(pdf_src)}" title="{escape(m.title)}" style="pointer-events:none; width:100%; height:100%;"></iframe>
                    </object>
                    <div style="position:absolute; inset:0; z-index:10; cursor:pointer; background:rgba(7,22,41,0.03); display:flex; align-items:flex-end; justify-content:center; padding-bottom:8px; transition:background 0.2s ease;">
                        <span style="font-size:0.6875rem; font-weight:800; color:var(--deep-frozen-midnight); background:rgba(255,255,255,0.95); padding:5px 12px; border-radius:20px; box-shadow:0 2px 8px rgba(7,22,41,0.18); border:1px solid var(--icy-steel-50); display:flex; align-items:center; gap:5px; cursor:pointer;">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Click to Read in Large Window
                        </span>
                    </div>
                </div>
                """
            else:
                type_pill = """
                <span style="background:var(--deep-frozen-midnight); color:var(--snow-white); padding:3px 8px; border-radius:var(--radius-xs); font-size:0.65625rem; font-weight:800; border:1px solid var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:5px; box-shadow:0 1px 3px rgba(23,52,92,0.2);">
                    <svg viewBox="0 0 24 24" style="width:12px; height:12px;" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    YOUTUBE VIDEO
                </span>
                """
                read_indicator = '<span style="font-size:0.6875rem; font-weight:700; color:var(--deep-frozen-midnight); display:inline-flex; align-items:center; gap:4px;">&#9654; In-Container Player</span>'
                vid = extract_youtube_video_id(m.url_or_data)
                embed_src = f"https://www.youtube.com/embed/{vid}"
                media_viewer_html = f"""
                <div class="media-video-box">
                    <iframe src="{embed_src}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen title="{escape(m.title)}"></iframe>
                </div>
                """

            # Management buttons for Guardian
            guardian_actions = ""
            if is_guardian:
                guardian_actions = f"""
                <button type="button" class="btn-secondary btn-sm" style="padding:4px 9px; font-size:0.71875rem; font-weight:700; display:inline-flex; align-items:center; gap:4px;" onclick="window.StarAppBridge.dispatchAction('open_edit_material_modal', '{m.id}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    Edit
                </button>
                <button type="button" class="btn-secondary btn-sm" style="padding:4px 9px; font-size:0.71875rem; font-weight:700; color:#d9534f; display:inline-flex; align-items:center; gap:4px;" onclick="if(confirm('Are you sure you want to delete this learning material?')) window.StarAppBridge.dispatchAction('delete_material', '{m.id}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    Delete
                </button>
                """

            mat_cards.append(f"""
            <div class="resource-media-card">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        {type_pill}
                        <span style="font-size:0.65625rem; font-weight:700; color:var(--frost-navy-50); text-transform:uppercase; letter-spacing:0.5px;">{escape(m.topic)}</span>
                    </div>
                    <h4 style="font-size:0.84375rem; font-weight:800; color:var(--frost-navy); margin:4px 0 2px 0; line-height:1.35; height:36px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;" title="{escape(m.title)}">{escape(m.title)}</h4>
                    <p style="font-size:0.71875rem; color:var(--frost-navy-75); line-height:1.4; margin:0 0 6px 0; height:32px; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;" title="{escape(m.description)}">{escape(m.description)}</p>

                    {media_viewer_html}
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; padding-top:10px; border-top:1px solid var(--icy-steel-30); margin-top:4px; flex-wrap:wrap; gap:6px;">
                    {read_indicator}
                    <div style="display:flex; align-items:center; gap:6px;">
                        <button type="button" class="btn-metal btn-sm" style="padding:4px 10px; font-size:0.71875rem; font-weight:700; display:inline-flex; align-items:center; gap:5px;" onclick="window.StarAppBridge.dispatchAction('view_material_preview', '{m.id}')" title="Open document/video in large view">
                            {get_icon("file_text" if m.material_type == "pdf" else "play", 12)} Theater View (Large Reader) &rarr;
                        </button>
                        {guardian_actions}
                    </div>
                </div>
            </div>
            """)

        mats_grid = f"""
        <div class="materials-grid" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(min(320px, 100%), 1fr)); gap:18px; align-items:stretch;">
            {"".join(mat_cards)}
        </div>
        """ if mat_cards else """
        <div style="padding:20px; text-align:center; color:var(--frost-navy-50); font-style:italic; background:rgba(234,244,255,0.4); border-radius:var(--radius-sm); border:1px dashed var(--icy-steel-50);">
            No learning resources of the selected format found for this milestone.
        </div>
        """

        badge_sections.append(f"""
        <!-- Badge Section: {escape(b.code)} -->
        <div class="badge-resource-section" style="background:#FFFFFF; border:1.5px solid var(--icy-steel-50); border-radius:var(--radius-md); padding:18px 20px; margin-bottom:24px; box-shadow:0 4px 16px rgba(7,22,41,0.04);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; padding-bottom:12px; border-bottom:1.5px solid var(--icy-steel-30); flex-wrap:wrap; gap:10px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-family:var(--font-family-mono); font-size:0.78125rem; font-weight:800; color:var(--snow-white); background:var(--deep-frozen-midnight); padding:3px 10px; border-radius:var(--radius-xs); letter-spacing:0.5px;">{escape(b.code)}</span>
                    <h3 style="font-size:1.25rem; font-weight:800; color:var(--frost-navy); margin:0;">{escape(b.title)}</h3>
                    <span style="font-size:0.6875rem; color:var(--frost-navy-50); background:rgba(23,52,92,0.06); padding:2px 7px; border-radius:var(--radius-xs); font-weight:600;">{escape(b.category)}</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:0.71875rem; font-weight:700; color:var(--deep-frozen-midnight); background:rgba(234,244,255,0.9); padding:3px 10px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50);">
                        {len(b_mats)} Available {"Resource" if len(b_mats) == 1 else "Resources"}
                    </span>
                </div>
            </div>

            {mats_grid}
        </div>
        """)

    # Empty State Handling
    if not materials:
        if is_guardian:
            content_body = """
            <div class="liquid-glass-card" style="padding:48px 24px; text-align:center;">
                <div style="width:52px; height:52px; border-radius:50%; background:rgba(23,52,92,0.08); display:flex; align-items:center; justify-content:center; margin:0 auto 14px; color:var(--deep-frozen-midnight);">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                </div>
                <h3 style="font-size:1.3rem; font-weight:800; color:var(--frost-navy); margin-bottom:6px;">No Learning Materials Published Yet</h3>
                <p style="font-size:0.84375rem; color:var(--frost-navy-50); max-width:480px; margin:0 auto 20px;">Upload curriculum syllabi, engineering whitepapers, and embedded YouTube video lectures for your Cosmonauts.</p>
                <button type="button" class="btn-metal" style="font-weight:800; font-size:0.8125rem; padding:10px 20px;" onclick="window.StarAppBridge.dispatchAction('open_add_material_modal', '{}')">
                    + Upload Learning Materials
                </button>
            </div>
            """
        else:
            content_body = """
            <div class="liquid-glass-card" style="padding:48px 24px; text-align:center;">
                <div style="width:52px; height:52px; border-radius:50%; background:rgba(23,52,92,0.08); display:flex; align-items:center; justify-content:center; margin:0 auto 14px; color:var(--deep-frozen-midnight);">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                </div>
                <h3 style="font-size:1.3rem; font-weight:800; color:var(--frost-navy); margin-bottom:6px;">No Learning Materials Available</h3>
                <p style="font-size:0.84375rem; color:var(--frost-navy-50); max-width:480px; margin:0 auto;">Your Training Guardian will publish milestone specifications, PDF handbooks, and video lectures here.</p>
            </div>
            """
    elif not badge_sections:
        content_body = """
        <div class="badge-resource-section" style="padding:48px 24px; text-align:center; color:var(--frost-navy-50); background:#FFFFFF; border:1.5px solid var(--icy-steel-50); border-radius:var(--radius-md);">
            <p style="font-size:0.9375rem; font-weight:700; color:var(--deep-frozen-midnight); margin-bottom:6px;">No learning resources matched your filter criteria.</p>
            <p style="font-size:0.8125rem; margin:0;">Try selecting "All Milestone Badges" or toggling the format filter to All.</p>
        </div>
        """
    else:
        content_body = "".join(badge_sections)

    return f"""
    <div>
        <!-- Top Title & Action Header -->
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
            <div>
                <h2 style="font-size:1.45rem; font-weight:800; color:var(--frost-navy); margin:0 0 4px 0;">{header_title}</h2>
                <p style="font-size:0.8125rem; color:var(--frost-navy-50); margin:0;">{header_desc}</p>
            </div>
            {header_action_html}
        </div>

        <!-- Filter Controls Bar -->
        <div class="liquid-glass-card" style="padding:14px 18px; margin-bottom:22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:14px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <label for="materials-badge-filter-select" style="font-size:0.75rem; font-weight:800; color:var(--deep-frozen-midnight); text-transform:uppercase; letter-spacing:0.5px;">Filter by Milestone:</label>
                <select id="materials-badge-filter-select" class="liquid-glass-control liquid-glass-select" style="font-size:0.78125rem; font-weight:700; padding:6px 12px; min-width:260px;" onchange="window.StarAppBridge.dispatchAction('filter_materials_badge', this.value)">
                    {"".join(badge_opts)}
                </select>
            </div>

            <div style="display:flex; align-items:center; gap:6px; background:rgba(234,244,255,0.7); padding:4px; border-radius:var(--radius-sm); border:1px solid var(--icy-steel-50);">
                <button type="button" style="{btn_all_style}" onclick="window.StarAppBridge.dispatchAction('filter_materials_type', 'all')">
                    All Formats ({count_all})
                </button>
                <button type="button" style="{btn_pdf_style}" onclick="window.StarAppBridge.dispatchAction('filter_materials_type', 'pdf')">
                    <svg viewBox="0 0 24 24" style="width:13px; height:13px;" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    PDF Documents ({count_pdf})
                </button>
                <button type="button" style="{btn_yt_style}" onclick="window.StarAppBridge.dispatchAction('filter_materials_type', 'youtube')">
                    <svg viewBox="0 0 24 24" style="width:13px; height:13px;" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    YouTube Videos ({count_yt})
                </button>
            </div>
        </div>

        <!-- Rendered Badge Resource Sections -->
        {content_body}
    </div>
    """


# ==============================================================================
# PROFESSIONAL ICONS: emoji / dingbat characters -> the vector icon set
# ==============================================================================
# Emoji render differently on every OS (and as colour bitmaps next to our line icons), which made the
# Cosmonaut / Reviewer portal look unfinished beside the Guardian portal. Rather than hand-editing
# hundreds of strings in the view modules (and every future one), the finished markup is passed through
# `iconize_html`, which swaps those characters for `get_icon(...)` SVGs.
#
# Safety: only TEXT NODES are touched. Tags are matched quote-aware (so `=>` inside an onclick attribute
# cannot fool it) and <option>/<textarea>/<title>/<script>/<style>/<select> contents are left alone.

import re as _re

_GLYPH_ICONS = {
    "&#10003;": "check", "\u2713": "check", "\u2714": "check",
    "&#10005;": "x", "&#10007;": "x", "\u2715": "x", "\u2717": "x", "\u2718": "x",
    "&#9888;": "alert_triangle", "\u26a0\ufe0f": "alert_triangle", "\u26a0": "alert_triangle",
    "&#9733;": "star", "\u2605": "star", "\u2b50": "star",
    "&#9873;": "flag", "\u2691": "flag",
    "&#129351;": "medal_1", "\U0001F947": "medal_1",
    "&#129352;": "medal_2", "\U0001F948": "medal_2",
    "&#129353;": "medal_3", "\U0001F949": "medal_3",
    "&#127942;": "award", "\U0001F3C6": "award", "\U0001F396\ufe0f": "award",
    "&#128197;": "calendar", "\U0001F4C5": "calendar", "\U0001F4C6": "calendar",
    "&#9200;": "clock", "\u23f0": "clock", "&#9203;": "clock", "\u23f3": "clock", "\u231b": "clock",
    "&#9999;": "edit", "\u270f\ufe0f": "edit", "\u270f": "edit", "\U0001F4DD": "edit", "\U0001F58A\ufe0f": "edit",
    "&#127891;": "book", "\U0001F393": "book", "\U0001F4DA": "book",
    "&#9878;": "scale", "\u2696\ufe0f": "scale", "\u2696": "scale",
    "&#128640;": "rocket", "\U0001F680": "rocket",
    "&#9889;": "flash", "\u26a1": "flash",
    "&#128101;": "users", "\U0001F465": "users", "\U0001F46A": "users",
    "\U0001F4C4": "file_text", "\U0001F4CB": "clipboard", "\U0001F4CA": "analytics", "\U0001F3AF": "target",
    "\U0001F514": "bell", "\U0001F512": "lock", "\U0001F513": "unlock", "\U0001F50D": "search",
    "\U0001F4C1": "folder", "\U0001F6E1\ufe0f": "shield", "\U0001F6E1": "shield",
    "\u2728": "flash", "&#10024;": "flash", "\U0001F4E5": "download", "\U0001F4E4": "download",
    "\U0001F4CE": "folder", "\U0001F517": "external_link", "\U0001F4A1": "flash", "\U0001F4C8": "analytics",
    "\U0001F4C9": "analytics", "\U0001F9E0": "target",
}
_GLYPH_RE = _re.compile("|".join(_re.escape(g) for g in sorted(_GLYPH_ICONS, key=len, reverse=True)))
# quote-aware tag / comment matcher (attribute values may legally contain ">" e.g. "x => x.checked")
_MARKUP_TOKEN_RE = _re.compile(r"""(<!--.*?-->|<(?:[^>"']|"[^"]*"|'[^']*')*>)|([^<]+)""", _re.S)
_RAW_TEXT_TAG_RE = _re.compile(r"<(/?)(option|textarea|title|script|style|select)\b", _re.I)


def _glyph_to_icon(match) -> str:
    return get_icon(_GLYPH_ICONS[match.group(0)], "1.1em", "margin-right:0.18em; vertical-align:-0.18em; flex-shrink:0;")


def iconize_html(markup: str) -> str:
    """Replaces emoji / dingbat characters in TEXT NODES of `markup` with professional SVG icons."""
    if not markup or not _GLYPH_RE.search(markup):
        return markup
    out = []
    raw_depth = 0
    for tok in _MARKUP_TOKEN_RE.finditer(markup):
        tag, text = tok.group(1), tok.group(2)
        if tag is not None:
            m = _RAW_TEXT_TAG_RE.match(tag)
            if m:
                raw_depth = max(0, raw_depth + (-1 if m.group(1) else 1))
            out.append(tag)
        elif raw_depth > 0:
            out.append(text)
        else:
            out.append(_GLYPH_RE.sub(_glyph_to_icon, text))
    return "".join(out)


def render_sidebar_actions_footer(current_user, nav_action: str, profile_view: str, active_view: str, subtitle: str = "") -> str:
    """
    The sidebar footer of EVERY portal (Guardian, Cosmonaut, Reviewer), bottom-left: the signed-in user's name card, and below it TWO buttons side by side -
    "View Profile" and "Sign Out" (equal-height, View Profile slightly wider). In the narrow 72 px rail the card is hidden and
    the two buttons stack as icons; when the sidebar expands they sit in one row. View Profile keeps `data-nav-id` + the
    `nav-link` class so the in-place active-highlight logic in bridge.js still marks it.
    """
    cls = "nav-link active" if active_view == profile_view else "nav-link"
    signout_ico = (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '<polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>'
    )
    return f"""
        <div class="sidebar-footer">
            <div class="lg-sidebar-profile is-card">
                <div class="lg-sidebar-profile-meta">
                    <div class="user-name">{escape(current_user.name)}</div>
                    <div class="user-role-text">{escape(subtitle)}</div>
                </div>
            </div>
            <ul class="sidebar-nav-bottom is-actions">
                <li class="nav-item is-wide">
                    <a class="{cls}" data-nav-id="{profile_view}" onclick="window.StarAppBridge.dispatchAction('{nav_action}', '{profile_view}')" title="View Profile">
                        {get_icon("user", 18)}
                        <span>View Profile</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a class="nav-link signout-link" role="button" onclick="window.StarAppBridge.dispatchAction('logout', '{{}}')" title="Sign Out">
                        {signout_ico}
                        <span>Sign Out</span>
                    </a>
                </li>
            </ul>
        </div>
    """


REVIEWER_BANDS = ("B2", "B3", "B4", "B5", "B6")
COSMONAUT_REVIEWER_VIEWS = frozenset({"c_badge_reviews", "c_requests", "c_badge_review", "c_assessment_detail"})


def is_reviewer_band(band) -> bool:
    """Reviewer_Band > Badge_Band: nobody in Band 1 can review anything, so reviewer tools start at Band 2."""
    return str(band or "").upper() in REVIEWER_BANDS


# ==============================================================================
# COSMONAUT PORTAL TERMINOLOGY: "Cadet" -> "Cosmonaut"
# ==============================================================================
_CADET_WORD_RE = _re.compile(r"\bcadet(s?)\b", _re.I)
_TEXT_ATTR_RE = _re.compile(r'(\s(?:placeholder|title|aria-label|alt)\s*=\s*)("[^"]*"|\'[^\']*\')', _re.I)
_SCRIPT_STYLE_TAG_RE = _re.compile(r"<(/?)(script|style)\b", _re.I)


def _cadet_to_cosmonaut(match) -> str:
    word = match.group(0)
    plural = match.group(1)
    if len(word) > 1 and word.isupper():
        return "COSMONAUTS" if plural else "COSMONAUT"
    base = "Cosmonaut" if word[0].isupper() else "cosmonaut"
    return base + ("s" if plural else "")


def cosmonaut_terms(markup: str) -> str:
    """
    The Cosmonaut portal calls its learners "Cosmonauts". Stored text (activity feeds, notifications, flash
    messages) and view literals may still say "Cadet", so the finished markup is normalised in one place:
    only visible TEXT NODES and the text attributes placeholder / title / aria-label / alt are rewritten
    (never ids, class names, onclick handlers, scripts or styles) and the original capitalisation is kept.
    """
    if not markup or not _CADET_WORD_RE.search(markup):
        return markup
    if "<" not in markup:
        return _CADET_WORD_RE.sub(_cadet_to_cosmonaut, markup)
    out = []
    raw_depth = 0
    for tok in _MARKUP_TOKEN_RE.finditer(markup):
        tag, text = tok.group(1), tok.group(2)
        if tag is not None:
            m = _SCRIPT_STYLE_TAG_RE.match(tag)
            if m:
                raw_depth = max(0, raw_depth + (-1 if m.group(1) else 1))
            if not tag.startswith("<!--") and _CADET_WORD_RE.search(tag):
                tag = _TEXT_ATTR_RE.sub(lambda a: a.group(1) + _CADET_WORD_RE.sub(_cadet_to_cosmonaut, a.group(2)), tag)
            out.append(tag)
        elif raw_depth > 0:
            out.append(text)
        else:
            out.append(_CADET_WORD_RE.sub(_cadet_to_cosmonaut, text))
    return "".join(out)


# ==============================================================================
# HUMAN-READABLE TEXT: internal ids -> names / badge codes
# ==============================================================================
_USER_ID_RE = _re.compile(r"\b(?:m_b[1-6]_\d+|cosmo_\d+|guardian_\d+)\b")
_BADGE_ID_RE = _re.compile(r"\bbadge_[a-z0-9]+(?:_[a-z0-9]+)*\b|\bb[1-6]_[a-z]{2,6}_\d{2}\b", _re.I)


def humanize_internal_ids(text: str) -> str:
    """
    Activity summaries were stored with raw ids ("Mapped m_b1_1 to ...", "badge_b1_sig_01_1795596050").
    Show people by name and badges by code instead. Unknown ids are left as they are.
    """
    if not text or ("_" not in text):
        return text or ""
    from starapp.storage import store

    def user_name(m):
        u = store.get_user_by_id(m.group(0))
        return u.name if u else m.group(0)

    def badge_code(m):
        raw = m.group(0)
        b = store.get_badge(raw)
        if not b:
            # ids with a trailing timestamp (badge_x_1795596050) -> try without it
            trimmed = _re.sub(r"_\d{8,}$", "", raw)
            b = store.get_badge(trimmed) if trimmed != raw else None
        return b.code if b else raw

    return _BADGE_ID_RE.sub(badge_code, _USER_ID_RE.sub(user_name, text))
