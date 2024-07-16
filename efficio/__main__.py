import argparse
import os
import importlib.util
import inspect

from typing import Type, List, Tuple, Optional, Union, Sequence, Any, Dict, get_type_hints

import efficio

def find_subclasses_in_directory(target_class: Type[Any], directory: str) -> List[Type[Any]]:
    subclasses = []

    # Traverse the directory to find all Python files
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                module_name = os.path.splitext(file_path)[0].replace(os.path.sep, '.')

                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, target_class) and obj is not target_class:
                            subclasses.append(obj)

    return subclasses

def get_constructor_params(cls: Type[Any]) -> Dict[str, Any]:
    sig = inspect.signature(cls.__init__)
    type_hints = get_type_hints(cls.__init__)
    params = {}
    for name, param in sig.parameters.items():
        if name == 'self':
            continue  # Skip the 'self' parameter
        param_type = type_hints.get(name, Any)
        params[name] = param_type.__name__
    
    return params


def fetch_object_data() -> Dict[str,Dict[str, str]]:
    main_directory = os.path.dirname(os.path.abspath(__file__))
    subclasses = find_subclasses_in_directory(efficio.EfficioObject, main_directory)

    result = {}
    for subclass in subclasses:
        class_name = subclass.__name__
        class_params = get_constructor_params(subclass)
        param_dict = {class_param: class_params[class_param] for class_param in class_params}
        result[class_name] = param_dict
            
    return result

def main(obj_name: str, obj_params: List[Tuple[str, str]]) -> None:
    pass

class parse_obj_params(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None
    ) -> None:
        params = getattr(namespace, self.dest, [])
        if type(values) != str:
            raise TypeError(f"Expected type string but got: {type(values).__name__}")
        key, value = values.split('=', 1)
        params.append((key, value))
        setattr(namespace, self.dest, params)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process some parameters.")

    options = fetch_object_data()
    print(options)
    
    parser.add_argument('--object', type=str, required=True, help='The name of the object')
    parser.add_argument('--params', action=parse_obj_params, help='Key-value pair parameters in the form key=value')

    args = parser.parse_args()

    main(args.object, args.params)
