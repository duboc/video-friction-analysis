from typing import Dict, Any

VIDEO_ANALYSIS_SCHEMA = {
  "type": "object",
  "required": ["executiveSummary", "frictionLog", "analysis", "recommendations", "conclusion"],
  "properties": {
    "executiveSummary": {
      "type": "array",
      "description": "3-5 bullet points summarizing key UX findings",
      "minItems": 3,
      "maxItems": 5,
      "items": {
        "type": "string",
        "minLength": 10  
      }
    },
    "frictionLog": {
      "type": "array",
      "description": "Detailed log of UX observations during testing",
      "items": {
        "type": "object",
        "required": ["timestamp", "task", "frictionPoint", "severity", "recommendation"],
        "properties": {
          "timestamp": {
            "type": "string",
            "description": "Time in the video where the issue occurs (e.g., MM:SS)",
            "pattern": "^[0-5]?[0-9]:[0-5]?[0-9]$" 
          },
          "task": {
            "type": "string",
            "description": "Specific action the user is trying to accomplish",
            "minLength": 5
          },
          "frictionPoint": {
            "type": "string",
            "description": "Exact element or interaction causing difficulty",
            "minLength": 5
          },
          "severity": {
            "type": "string",
            "enum": ["High", "Medium", "Low"],
            "description": "Impact rating of the friction point"
          },
          "recommendation": {
            "type": "string",
            "description": "Suggested improvement to address the friction point",
            "minLength": 10
          }
        }
      }
    },
    "analysis": {
      "type": "object",
      "required": ["taskFlow", "interactionDesign", "informationArchitecture", "visualDesign"],
      "properties": {
        "taskFlow": {
          "type": "object",
          "required": ["efficiency", "clarity", "findings"],
          "properties": {
            "efficiency": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5"},
            "clarity": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5"},
            "findings": {"type": "array", "items": {"type": "string", "minLength": 10}}
          }
        },
        "interactionDesign": {  "type": "object", "required": ["usability", "responsiveness","findings"], "properties": { "usability": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5" }, "responsiveness": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5" }, "findings": { "type": "array", "items": { "type": "string", "minLength": 10 } } } },
        "informationArchitecture": { "type": "object", "required": ["findability", "organization", "findings"], "properties": { "findability": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5" }, "organization": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5" }, "findings": { "type": "array", "items": { "type": "string", "minLength": 10 } } } },
        "visualDesign": { "type": "object", "required": ["aesthetics", "branding", "findings"], "properties": { "aesthetics": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5" }, "branding": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Rating on a scale of 1-5" }, "findings": { "type": "array", "items": { "type": "string", "minLength": 10 } } } }
      }
    },
    "recommendations": {
      "type": "array",
      "description": "Prioritized list of key usability issues and solutions",
      "items": {
        "type": "object",
        "required": ["issue", "priority", "solution", "impact"],
        "properties": {
          "issue": { "type": "string", "description": "Description of the usability issue", "minLength": 10 },
          "priority": { "type": "string", "enum": ["High", "Medium", "Low"] },
          "solution": { "type": "string", "description": "Concrete suggestion for addressing the issue", "minLength": 10 },
          "impact": { "type": "string", "description": "Expected impact of implementing the solution", "minLength": 10 }
        }
      }
    },
    "conclusion": {
      "type": "object",
      "required": ["strengths", "weaknesses", "overallScore"],
      "properties": {
        "strengths": { "type": "array", "items": { "type": "string", "minLength": 5 } },
        "weaknesses": { "type": "array", "items": { "type": "string", "minLength": 5 } },
        "overallScore": { "type": "integer", "minimum": 1, "maximum": 5, "description": "Overall UX score on a scale of 1-5" }
      }
    }
  }
}

USER_STORY_SCHEMA = {
    "type": "object",
    "required": ["userStories"],
    "properties": {
        "userStories": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "priority",
                    "userStory",
                    "painPoint",
                    "proposedSolution",
                    "complexity",
                    "businessValue",
                    "acceptanceCriteria"
                ],
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["Critical", "High", "Medium", "Low"],
                        "description": "Priority level based on impact to core functionality and business"
                    },
                    "userStory": {
                        "type": "string",
                        "description": "Formatted as: 'As a [user type], I want to [specific action] so that [clear benefit]'"
                    },
                    "painPoint": {
                        "type": "string",
                        "description": "Clear description of the current issue from friction log"
                    },
                    "proposedSolution": {
                        "type": "object",
                        "required": ["description", "implementation"],
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "High-level solution description"
                            },
                            "implementation": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific implementation steps"
                            }
                        }
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["Simple", "Medium", "Complex"],
                        "description": "Estimated implementation complexity"
                    },
                    "businessValue": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                        "description": "Expected business impact"
                    },
                    "acceptanceCriteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific, measurable criteria for story completion"
                    },
                    "implementationNotes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technical considerations and implementation details"
                    }
                }
            }
        },
        "metadata": {
            "type": "object",
            "properties": {
                "totalStories": {"type": "integer"},
                "priorityBreakdown": {
                    "type": "object",
                    "properties": {
                        "critical": {"type": "integer"},
                        "high": {"type": "integer"},
                        "medium": {"type": "integer"},
                        "low": {"type": "integer"}
                    }
                },
                "complexityBreakdown": {
                    "type": "object",
                    "properties": {
                        "simple": {"type": "integer"},
                        "medium": {"type": "integer"},
                        "complex": {"type": "integer"}
                    }
                }
            }
        }
    }
}

TASK_BACKLOG_SCHEMA = {
    "type": "object",
    "required": ["userStoryTasks"],
    "properties": {
        "userStoryTasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["userStoryID", "userStoryTitle", "tasks"],
                "properties": {
                    "userStoryID": {
                        "type": "string",
                        "description": "Unique identifier for the user story"
                    },
                    "userStoryTitle": {
                        "type": "string",
                        "description": "Brief, descriptive title of the user story"
                    },
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "taskID",
                                "taskDescription",
                                "estimatedEffortHours",
                                "priority",
                                "requiresCode"
                            ],
                            "properties": {
                                "taskID": {
                                    "type": "string",
                                    "description": "Categorized task identifier"
                                },
                                "taskDescription": {
                                    "type": "string",
                                    "description": "Specific, actionable task description"
                                },
                                "estimatedEffortHours": {
                                    "type": "number",
                                    "description": "Estimated effort in hours"
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["High", "Medium", "Low"],
                                    "description": "Task priority level"
                                },
                                "requiresCode": {
                                    "type": "boolean",
                                    "description": "Indicates if task requires code changes"
                                },
                                "dependencies": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of dependent task IDs"
                                },
                                "category": {
                                    "type": "string",
                                    "enum": [
                                        "UI/UX Development",
                                        "Backend Development",
                                        "Database Operations",
                                        "API Development",
                                        "Testing & Quality Assurance",
                                        "Documentation",
                                        "Security & Compliance",
                                        "Infrastructure & DevOps",
                                        "Research & Analysis"
                                    ],
                                    "description": "Task category"
                                },
                                "completionCriteria": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Specific criteria for task completion"
                                }
                            }
                        }
                    }
                }
            }
        },
        "summary": {
            "type": "object",
            "properties": {
                "totalUserStories": {"type": "integer"},
                "totalTasks": {"type": "integer"},
                "totalEffortHours": {"type": "number"},
                "averageTasksPerStory": {"type": "number"},
                "priorityBreakdown": {
                    "type": "object",
                    "properties": {
                        "high": {"type": "integer"},
                        "medium": {"type": "integer"},
                        "low": {"type": "integer"}
                    }
                }
            }
        }
    }
} 