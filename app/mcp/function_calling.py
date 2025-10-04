from pydantic import BaseModel, Field
from typing import Callable, Dict, Any, List, Type, Union, Optional
import inspect
import json

class FunctionParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True

class FunctionDefinition(BaseModel):
    """
    Standardized function definition schema
    """
    name: str = Field(..., description="Name of the function")
    description: str = Field(..., description="Description of the function")
    parameters: List[FunctionParameter] = Field(
        default_factory=list, 
        description="List of parameters"
    )
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description
                    } for param in self.parameters
                },
                "required": [param.name for param in self.parameters if param.required]
            }
        }

class FunctionHandler:
    """
    Registry for tool functions with standardized calling
    """
    _registry: Dict[str, Callable] = {}
    _definitions: Dict[str, FunctionDefinition] = {}
    
    @classmethod
    def register(
        cls, 
        func: Callable, 
        name: Optional[str] = None,
        description: Optional[str] = None
    ):
        """Register a function with metadata"""
        name = name or func.__name__
        description = description or func.__doc__ or name
        
        # Extract parameters from function signature
        parameters = []
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "string"
            parameters.append(FunctionParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter: {param_name}",
                required=param.default == inspect.Parameter.empty
            ))
        
        # Create and store function definition
        definition = FunctionDefinition(
            name=name,
            description=description,
            parameters=parameters
        )
        
        cls._registry[name] = func
        cls._definitions[name] = definition
        return func
    
    @classmethod
    def get_function(cls, name: str) -> Callable:
        """Get a registered function by name"""
        return cls._registry.get(name)
    
    @classmethod
    def get_definitions(cls) -> List[Dict[str, Any]]:
        """Get all function definitions in JSON schema format"""
        return [defn.to_json_schema() for defn in cls._definitions.values()]
    
    @classmethod
    def execute(
        cls, 
        function_name: str, 
        arguments: Union[str, Dict[str, Any]]
    ) -> Any:
        """Execute a function with arguments"""
        func = cls.get_function(function_name)
        if not func:
            raise ValueError(f"Function '{function_name}' not found")
        
        # Parse arguments if needed
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON arguments")
        
        # Call the function
        return func(**arguments)
