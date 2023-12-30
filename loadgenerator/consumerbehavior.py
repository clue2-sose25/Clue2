from random import randint
from locust import HttpUser, task, between
from typing import MutableSet
from datetime import datetime
import hashlib
from random import choice, seed
from abc import ABC, abstractclassmethod, abstractmethod, abstractproperty, abstractstaticmethod
import json
 
import config as CFG


class ConsumerBehaviourModelGraph(HttpUser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class CBMGState:

        def __init__(self, id) -> None:
            self.id = id
            self.nodes: set[ConsumerBehaviourModelGraph.CBMGState.CBMGNode] = set()
            self.edges: set[ConsumerBehaviourModelGraph.CBMGState.CBMGEdge] = set()
            self.currentState: ConsumerBehaviourModelGraph.CBMGState.CBMGNode = None

        class CBMGEdge:

            def __init__(self, upstream, downstream, weight) -> None:
                self.upstream: ConsumerBehaviourModelGraph.CBMGState.CBMGNode = upstream
                self.downstream: ConsumerBehaviourModelGraph.CBMGState.CBMGNode = downstream
                self.weight: int = weight

        class CBMGNode:

            def __init__(self, name, task) -> None:
                self.name = name
                self.outgoing: MutableSet[ConsumerBehaviourModelGraph.CBMGState.CBMGEdge] = set(
                )
                self.task = task

            def get_outgoing_sum(self) -> int:
                out_sum = 0
                for edge in self.outgoing:
                    out_sum += edge.weight
                return out_sum

            def get_out_percentages(self) -> dict:
                out_percentage = dict()
                one = self.get_outgoing_sum()

                for edge in self.outgoing:
                    out_percentage.update(
                        {edge.downstream.name: edge.weight/one})

                return out_percentage

            def __repr__(self) -> str:
                return f"CBMGNode(name={self.name},task={self.task.__name__})"

        def addNode(self, task_object):
            task_object: Vanilla = task_object
            newNode = self.CBMGNode(task_object.name, task_object.task)

            self.nodes.add(newNode)

            return newNode

        def getNode(self, name):
            for n in self.nodes:
                if n.name == name:
                    return n

        def get_nodes(self) -> set:
            return self.nodes

        def addEdge(self, start, end, weight):
            newEdge = ConsumerBehaviourModelGraph.CBMGState.CBMGEdge(
                start, end, weight)
            self.edges.add(newEdge)

            start: ConsumerBehaviourModelGraph.CBMGState.CBMGNode = start
            start.outgoing.add(newEdge)

            return newEdge

        def setStartState(self, state):
            if self.currentState == None:
                self.currentState = state
            else:
                raise RuntimeError

        def moveToState(self, newState):
            if self.currentState == None:
                raise RuntimeError

            for possibleState in self.currentState.outgoing:
                if newState == possibleState.downstream:
                    self.currentState = newState
                    return

            raise ValueError

        def generateTasklist(self):
            if self.currentState == None:
                raise RuntimeError

            tasklist = dict()
            for edge in self.currentState.outgoing:
                tasklist.update({edge.downstream.task: edge.weight})

            return tasklist

    def unpack(d: dict) -> list:
        arr = []
        for key, value in d.items():
            arr += [key] * value
        return arr

    def moveToState(self, newState):
        # print(f"moves {self.id} from {self.state.currentState} to {newState}")
        self.state.moveToState(newState)
        self.task_list = ConsumerBehaviourModelGraph.unpack(
            self.state.generateTasklist())

    def on_start(self):
        self.id = hashlib.sha256((datetime.now().isoformat(
        ) + str(randint(0, 200000))).encode()).hexdigest()[0:8]
        seed(self.id)
        # print(f"ID for new runner: {self.id}")

        endpoint = None
        if CFG.endpoint_name == "Vanilla":
            endpoint = Vanilla
        elif CFG.endpoint_name in ["SSG", "StaticSiteGeneration", "StaticSiteGenerator"]:
            endpoint = StaticSiteGeneration
        else:
            print("Failed to set an Endpoint Class.")
        # print("Using Endpoint: ", CFG.endpoint_name, endpoint, flush=True)

        self.state = self.CBMGState(id=self.id)

        entry_task = Entry(endpoint=endpoint)
        entry = self.state.addNode(entry_task)

        browse_task = Browse(endpoint=endpoint)
        browse = self.state.addNode(browse_task)

        addtocart_task = AddToCart(endpoint=endpoint)
        addToCart = self.state.addNode(addtocart_task)

        select_task = Select(endpoint=endpoint)
        select = self.state.addNode(select_task)

        pay_task = Pay(endpoint=endpoint)
        pay = self.state.addNode(pay_task)

        exit_task = Exit(endpoint=endpoint)
        _exit = self.state.addNode(exit_task)

        self.state.addEdge(entry, browse, 1)

        self.state.addEdge(browse, browse, 20)
        self.state.addEdge(browse, select, 9)
        self.state.addEdge(browse, _exit, 1)

        self.state.addEdge(addToCart, browse, 20)
        self.state.addEdge(addToCart, select, 3)
        self.state.addEdge(addToCart, pay, 6)
        self.state.addEdge(addToCart, _exit, 1)

        self.state.addEdge(select, browse, 32)
        self.state.addEdge(select, addToCart, 6)
        self.state.addEdge(select, _exit, 2)

        self.state.addEdge(pay, _exit, 1)

        self.state.addEdge(_exit, _exit, 9)
        self.state.addEdge(_exit, entry, 1)

        # for node in self.state.get_nodes():
        #     node: ConsumerBehaviourModelGraph.CBMGState.CBMGNode = node
        #     print(node.name, node.get_out_percentages())

        self.state.setStartState(entry)
        # print(f"Start Task: {entry.name}")

        self.task_list = ConsumerBehaviourModelGraph.unpack(
            self.state.generateTasklist())

    @task()
    def execute_task(self):
        choice(self.task_list)(self)

    wait_time = between(1, 5)


class Endpoints(ABC):

    _default_user_firstname = "Jon"
    _default_user_lastname = "Snow"
    _default_user_address_1 = "Winterfell"
    _default_user_address_2 = "11111 The North, Westeros"
    _default_user_cardtype = "Visa"
    _default_user_cardnumber = "314159265359"
    _default_user_expirydate = "12/2025"

    _default_user_data_list = [
        _default_user_firstname,
        _default_user_lastname,
        _default_user_address_1,
        _default_user_address_2,
        _default_user_cardtype,
        _default_user_cardnumber,
        _default_user_expirydate
    ]

    _default_user_data_dict = {
        "firstname":_default_user_firstname,
        "lastname":_default_user_lastname,
        "address":_default_user_address_1,
        "address2":_default_user_address_2,
        "cardtype":_default_user_cardtype,
        "cardnumber":_default_user_cardnumber,
        "expirydate":_default_user_expirydate
    }

    @abstractmethod
    def _get_homepage(user: ConsumerBehaviourModelGraph):
        pass

    _category_min = 2
    _category_max = 6
    _pages_min = 1
    _pages_max = 5

    def _get_category(user: ConsumerBehaviourModelGraph, category: int, page: int, fail: bool = False):
        pass

    _product_id_min = 8
    _product_id_max = 506

    def check_product_id(product_id: int, fail: bool):
        if product_id < Vanilla._product_id_min:
            if fail:
                raise ValueError
            product_id = Vanilla._product_id_min
        elif product_id > Vanilla._product_id_max:
            if fail:
                raise ValueError
            product_id = Vanilla._product_id_max
        return product_id

    def _get_product(user: ConsumerBehaviourModelGraph, product_id: int, fail: bool = False):
        pass

    def _add_product(user: ConsumerBehaviourModelGraph, product_id: int, fail: bool = False):
        pass

    def _pay_for_cart(user: ConsumerBehaviourModelGraph, products: dict[int: int], fail: bool = False):
        pass

    def _get_cart(user: ConsumerBehaviourModelGraph):
        pass

    def _get_order(user: ConsumerBehaviourModelGraph):
        pass


class Vanilla(Endpoints):

    def _get_homepage(user: ConsumerBehaviourModelGraph):
        user.client.get("", timeout=300)

    _category_min = 2
    _category_max = 6
    _pages_min = 1
    _pages_max = 5

    def _get_category(user: ConsumerBehaviourModelGraph, category: int, page: int, fail: bool = False):
        if category > Vanilla._category_max:
            if fail:
                raise ValueError
            category = Vanilla._category_max
        elif category < Vanilla._category_min:
            if fail:
                raise ValueError
            category = Vanilla._category_min

        if page > Vanilla._pages_max:
            if fail:
                raise ValueError
            page = Vanilla._pages_max
        elif page < Vanilla._pages_min:
            if fail:
                raise ValueError
            page = Vanilla._pages_min

        url = f"/category?category={category}&page={page}"
        user.client.get(url=url, name="/category", timeout=300)

    _product_id_min = 8
    _product_id_max = 506

    def check_product_id(product_id: int, fail: bool):
        return Endpoints.check_product_id(product_id, fail)

    def _get_product(user: ConsumerBehaviourModelGraph, product_id: int, fail: bool = False):
        product_id = Vanilla.check_product_id(product_id=product_id, fail=fail)

        url = f"/product?id={product_id}"
        user.client.get(url=url, name="/product", timeout=300)

    def _add_product(user: ConsumerBehaviourModelGraph, product_id: int, fail: bool = False):
        product_id = Vanilla.check_product_id(product_id=product_id, fail=fail)

        add_to_cart_data = f"productid={product_id}&addToCart='Add+to+Cart'"
        user.client.post("/cartAction", data=add_to_cart_data,
                         name="/cartAction | add to cart", timeout=300)

    def _pay_for_cart(user: ConsumerBehaviourModelGraph, products: dict[int: int], fail: bool = False):
        add_to_cart_data = f""
        for key, value in products.items():
            add_to_cart_data += f"productid={key}&orderitem_{key}={value}&"
        add_to_cart_data += f"proceedtoCheckout='Proceed+to+Checkout'"
        user.client.post("/cartAction", data=add_to_cart_data,
                         name="/cartAction | pay", timeout=300)

    def _get_cart(user: ConsumerBehaviourModelGraph):
        user.client.get("/cart", timeout=300)

    def _get_order(user: ConsumerBehaviourModelGraph):
        user.client.get("/order", timeout=300)


class StaticSiteGeneration(Endpoints):
    def _get_homepage(user: ConsumerBehaviourModelGraph):
        user.client.get("", timeout=300)

    def _get_category(user: ConsumerBehaviourModelGraph, category: int, page: int, fail: bool = False):
        if category > Vanilla._category_max:
            if fail:
                raise ValueError
            category = Vanilla._category_max
        elif category < Vanilla._category_min:
            if fail:
                raise ValueError
            category = Vanilla._category_min

        url = f"/category/{category}"
        user.client.get(url=url, timeout=300)

    def check_product_id(product_id: int, fail: bool):
        return Endpoints.check_product_id(product_id, fail)

    def _get_product(user: ConsumerBehaviourModelGraph, product_id: int, fail: bool = False):
        product_id = Vanilla.check_product_id(product_id=product_id, fail=fail)

        url = f"/products/{product_id}"
        user.client.get(url=url, name="/products", timeout=300)
        user.client.get(
            url=f"/api/recommendations/{product_id}", name="/api/recommendations/<id>")

    def _add_product(user: ConsumerBehaviourModelGraph, product_id: int, fail: bool = False):
        product_id = Vanilla.check_product_id(product_id=product_id, fail=fail)

        user.client.post(f"/api/cart/{product_id}",
                         name="/api/cart | POST", timeout=300)

    def _pay_for_cart(user: ConsumerBehaviourModelGraph, products: dict[int: int], fail: bool = False):
        for key, value in products.items():
            pass
        headers = {
            "Content-Type": "application/json"
        }

        body = json.dumps(StaticSiteGeneration._default_user_data_dict, separators=(',', ':'))

        user.client.post(f"/api/order", headers=headers,
                         data=body, name="/api/order | POST", timeout=300)

    def _get_cart(user: ConsumerBehaviourModelGraph):
        user.client.get("/cart", timeout=300)
        user.client.get("/api/recommendations", timeout=300)
        user.client.get("/api/cart", timeout=300)

    def _get_order(user: ConsumerBehaviourModelGraph):
        user.client.get("/order", timeout=300)


class Task:

    def __init__(self, name=None, endpoint: Endpoints = None) -> None:
        self.name = name or type(self).__name__

        self.endpoint = endpoint or Vanilla

    def task(self, user: ConsumerBehaviourModelGraph):
        user.moveToState(user.state.getNode(self.name))


class Entry(Task):

    def task(self, user: ConsumerBehaviourModelGraph):
        super().task(user)
        self.endpoint._get_homepage(user)


class Browse(Task):

    def task(self, user: ConsumerBehaviourModelGraph):
        super().task(user)
        self.endpoint._get_category(user, randint(self.endpoint._category_min, self.endpoint._category_max), randint(
            self.endpoint._pages_min, self.endpoint._pages_max))


class AddToCart(Task):
    def task(self, user: ConsumerBehaviourModelGraph):
        super().task(user)
        self.endpoint._add_product(user, randint(
            self.endpoint._product_id_min, self.endpoint._product_id_max))
        self.endpoint._get_cart(user)


class Select(Task):
    def task(self, user: ConsumerBehaviourModelGraph):
        super().task(user)
        self.endpoint._get_product(user, randint(
            self.endpoint._product_id_min, self.endpoint._product_id_max))


class Pay(Task):
    def task(self, user: ConsumerBehaviourModelGraph):
        super().task(user)
        products = dict()
        for i in range(randint(1, 10)):
            products.update(
                {
                    self.endpoint.check_product_id(
                        randint(
                            self.endpoint._product_id_min,
                            self.endpoint._product_id_max), False):
                    randint(
                        1,
                        5
                    )
                }
            )
        self.endpoint._pay_for_cart(user, products=products)
        self.endpoint._get_order(user)


class Exit(Task):

    def task(self, user: ConsumerBehaviourModelGraph):
        super().task(user)
