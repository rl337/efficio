import argparse

from typing import List, Tuple, Optional, Union, Sequence, Any

def main(obj_name: str, obj_params: List[Tuple[str, str]]) -> None:
    print(obj_name, obj_params)

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
    
    parser.add_argument('--object', type=str, required=True, help='The name of the object')
    parser.add_argument('--params', action=parse_obj_params, help='Key-value pair parameters in the form key=value')

    args = parser.parse_args()

    main(args.object, args.params)
