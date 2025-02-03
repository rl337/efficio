import argparse
import sys
import os
import importlib.util
import inspect

from typing import Type, List, Tuple, Optional, Union, Sequence, Any, Dict, get_type_hints, NoReturn

import efficio
import efficio.renderer

def find_subclasses_in_directory(target_class: Type[Any], directory: str) -> List[Type[Any]]:
    subclasses = []

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


def fetch_object_data() -> Dict[Type[Any],Dict[str, str]]:
    main_directory = os.path.dirname(os.path.abspath(__file__))
    subclasses = find_subclasses_in_directory(efficio.EfficioObject, main_directory)

    result = {}
    for subclass in subclasses:
        class_params = get_constructor_params(subclass)
        param_dict = {class_param: class_params[class_param] for class_param in class_params}
        result[subclass] = param_dict
            
    return result


def print_valid_classes(message: str, options: Dict[Type[Any],Dict[str, str]], only_class: str = "") -> None:
    if message:
        sys.stderr.write(f'\nError: {message}\n\n')
        sys.stderr.write('Please provide the required arguments as shown in the usage message above.\n')

    for obj_class in options:
        obj_name = obj_class.__name__
        params = ['--object', obj_name]
        obj_params = options[obj_class]
        for param_name in obj_params:
            params.append(f'--params {param_name}=<{obj_params[param_name]}>')
        sys.stderr.write(' '.join(params))
        sys.stderr.write("\n")


class EfficioArgumentParser(argparse.ArgumentParser):

    def error(self, message: str) -> NoReturn:
        options = fetch_object_data()
        print_valid_classes(message, options)

        sys.exit(2)

def str_to_bool(value: str) -> bool:
    if value.lower() in {'true', 'yes', 'y', '1'}:
        return True
    elif value.lower() in {'false', 'no', 'n', '0'}:
        return False
    else:
        raise ValueError(f"Invalid boolean value: '{value}'")


def main(obj_name: str, obj_params: Optional[List[Tuple[str, str]]], png_file: Optional[str], stl_file: Optional[str]) -> None:
    options = fetch_object_data()

    if obj_params is None:
        obj_params = []

    option_names = {x.__name__: x for x in options}
    if obj_name not in option_names:
        print_valid_classes(f"{obj_name} is not a valid object", options) 
        sys.exit(2)
    obj_class = option_names[obj_name]
    obj_param_dict = { x[0]: x[1] for x in obj_params }
    
    option_params = options[obj_class]
    kwargs: Dict[str, Any] = {}
    for option_name in option_params:
        option_type = option_params[option_name]
        if option_name not in obj_param_dict:
            print_valid_classes(f"{option_name} is required for {obj_name}", options)
            sys.exit(3)
        option_value = obj_param_dict[option_name]

        if option_type == 'Measure':
            kwargs[option_name] = efficio.parse_measure(option_value)            
        elif option_type == 'bool':
            kwargs[option_name] = str_to_bool(option_value)
        else:
            kwargs[option_name] = option_value

    obj_class = option_names[obj_name]
    instance = obj_class(**kwargs)
    shape = instance.shape()
    if not hasattr(shape, 'workplane'):
        print_valid_classes(f'{obj_name} is not a cadquery shape', options)
        sys.exit(4)

    if png_file:
        image = efficio.renderer.create_composite_image(shape.workplane())
        image.save(png_file, 'PNG')

    if stl_file:
        shape.as_stl_file(stl_file)

class parse_obj_params(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Sequence[Any], None],
        option_string: Optional[str] = None
    ) -> None:
        params = getattr(namespace, self.dest, None)
        if params is None:
            params = []
        if type(values) != str:
            raise TypeError(f"Expected type string but got: {type(values).__name__}")
        key, value = values.split('=', 1)
        params.append((key, value))
        setattr(namespace, self.dest, params)

if __name__ == '__main__':
    parser = EfficioArgumentParser(description="Process some parameters.")
    
    parser.add_argument('--object', type=str, required=True, help='The name of the object')
    parser.add_argument('--params', action=parse_obj_params, help='Key-value pair parameters in the form key=value')
    parser.add_argument('--png', type=str, help='Write as a PNG to this file.')
    parser.add_argument('--stl', type=str, help='Write as an STL to this file.')

    args = parser.parse_args()
    main(args.object, args.params, args.png, args.stl)
